from typing import Callable, List
import os
from dotenv import load_dotenv
import shutil
import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from fastapi import UploadFile
from minio import Minio
from .structures import UploadedFile
import hashlib


load_dotenv()


class FileHandler:
    def __init__(self, cfg: dict):
        self._configure(cfg)

    def upload_file(self, in_file: UploadFile) -> tuple[bool, None | str]:
        is_ok = self._check_file_type(in_file.content_type)
        if not is_ok:
            return False, None
        local_file_path = self._save_upload_file_tmp(in_file)
        dest_file = self._file_to_bucket(local_file_path)
        Path(local_file_path).unlink(missing_ok=True)
        return True, dest_file

    def get_ocr_result(
        self, file_uri: str, actual_ocr_file: UploadFile
    ) -> dict[str, any]:
        ## Mock OCR process
        content = actual_ocr_file.file.read()
        data = json.loads(content.decode("utf-8"))
        actual_ocr_file.file.close()
        return data

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
            access_key=os.getenv("MINIO_ACCESS_KEY"),
            secret_key=os.getenv("MINIO_SECRET_KEY"),
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

    def _save_upload_file_tmp(self, upload_file: UploadFile) -> str:
        try:
            suffix = os.path.splitext(upload_file.filename)[-1]
            filename = self._get_file_hash(upload_file) + suffix
            tmp_path = os.path.join(self.tmp_dir, filename)
            print(f"{tmp_path=}")
            with open(tmp_path, "wb") as f:
                shutil.copyfileobj(upload_file.file, f)
        finally:
            upload_file.file.close()
        return tmp_path

    def _file_to_bucket(self, local_file_path: str) -> str:
        dest_file = os.path.basename(local_file_path)
        self.client.fput_object(self.bucket_name, dest_file, local_file_path)
        return dest_file
    
    @staticmethod
    def _get_file_hash(file: UploadFile, hash_algorithm=hashlib.md5) -> str:
        file_hash = hash_algorithm()
        while content := file.file.read(4096):
            file_hash.update(content)
        file.file.seek(0)
        return file_hash.hexdigest()
