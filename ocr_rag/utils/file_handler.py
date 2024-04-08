from typing import List
import os
from dotenv import load_dotenv
from datetime import datetime
import unicodedata
import shutil
import json
from pathlib import Path
from fastapi import UploadFile
from minio import Minio
import hashlib
from openai import OpenAI

from .structures import UploadedFile
from .misc import translate

load_dotenv()


class FileHandler:
    def __init__(self, cfg: dict):
        self._configure(cfg)

    def upload_file(self, in_file: UploadFile) -> tuple[bool, None | UploadedFile]:
        is_ok = self._check_file_type(in_file.content_type)
        if not is_ok:
            return False, None
        uploaded_file, local_file_path = self._save_upload_file_tmp(in_file)
        dest_file = self._file_to_bucket(uploaded_file, local_file_path)
        Path(local_file_path).unlink(missing_ok=True)
        uploaded_file.path = dest_file
        return True, uploaded_file

    def get_ocr_result(
        self, file_uuid: str, actual_ocr_file: UploadFile, do_translate: bool = False
    ) -> str:
        ## Mock OCR process
        # data = self._get_file(file_uuid)
        # do something with data

        content = actual_ocr_file.file.read()
        data = json.loads(content.decode("utf-8"))
        actual_ocr_file.file.close()
        content = data["analyzeResult"]["content"]
        if do_translate:
            content = do_translate(content, os.environ.get("OPENAI_API_KEY"))
        return content

    def get_file_paths(self) -> List[str]:
        objects = self.client.list_objects(self.bucket_name, recursive=True)
        file_paths = [obj.object_name for obj in objects]
        return file_paths

    def remove_file(self, file_path: str):
        self.client.remove_object(self.bucket_name, file_path)

    def _configure(self, cfg: dict):
        self.cfg = cfg
        self.client = Minio(
            f"{cfg['uri']}:{cfg['port']}",
            access_key=cfg["MINIO_ACCESS_KEY"],
            secret_key=cfg["MINIO_SECRET_KEY"],
            secure=False,
        )
        self.bucket_name = cfg["bucket"]
        if not self.client.bucket_exists(self.bucket_name):
            self.client.make_bucket(self.bucket_name)
        self.tmp_dir = cfg["tmp_dir"]
        if not os.path.isdir(self.tmp_dir):
            Path(self.tmp_dir).mkdir(parents=True, exist_ok=True)
        self.allowed_types = cfg["allowed_types"]

    def _check_file_type(self, file_type: str):
        return file_type in self.allowed_types

    def _get_allowed_extensions(self):
        return ", ".join([t.split("/")[1] for t in self.allowed_types])

    def _save_upload_file_tmp(
        self, upload_file: UploadFile
    ) -> tuple[UploadedFile, str]:
        try:
            suffix = os.path.splitext(upload_file.filename)[-1]
            uuid = self._get_file_hash(upload_file)
            filename = uuid + suffix
            tmp_path = os.path.join(self.tmp_dir, filename)
            uploaded_file = UploadedFile(
                uuid=uuid,
                name=upload_file.filename,
                filetype=suffix[1:],
                date=datetime.now(),
            )
            with open(tmp_path, "wb") as f:
                shutil.copyfileobj(upload_file.file, f)
            return uploaded_file, tmp_path
        finally:
            upload_file.file.close()

    def _file_to_bucket(self, uploaded_file: UploadFile, local_file_path: str) -> str:
        dest_file = os.path.basename(local_file_path)
        metadata = {
            k: self._convert_to_ascii(v)
            for k, v in uploaded_file.model_dump(mode="json").items()
            if v
        }
        self.client.fput_object(
            self.bucket_name, uploaded_file.uuid, local_file_path, metadata=metadata
        )
        return dest_file

    def _get_file(self, uuid: str):
        try:
            response = self.client.get_object(self.bucket_name, uuid)
            if response.status != 200:
                return None
            response_data = response.data
            return response_data
        except:
            return None
        finally:
            response.close()
            response.release_conn()

    @staticmethod
    def _get_file_hash(file: UploadFile, hash_algorithm=hashlib.md5) -> str:
        file_hash = hash_algorithm()
        while content := file.file.read(4096):
            file_hash.update(content)
        file.file.seek(0)
        return file_hash.hexdigest()

    @staticmethod
    def _convert_to_ascii(input_string):
        normalized_string = unicodedata.normalize("NFKD", input_string)
        ascii_string = normalized_string.encode("ascii", "ignore").decode("ascii")
        return ascii_string
