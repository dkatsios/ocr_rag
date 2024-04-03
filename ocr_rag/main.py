import os
import yaml
from fastapi import FastAPI, File, UploadFile, HTTPException

from ocr_rag.utils import FileHandler, UploadedFile, get_cfg

app = FastAPI()

cur_dir = os.path.abspath(os.path.dirname(__file__))
cfg_path = os.path.join(os.path.dirname(cur_dir), "cfg.yaml")
cfg = get_cfg(cfg_path)
file_handler = FileHandler(cfg["file_handler"])


@app.post("/upload", response_model=UploadedFile)
def updload_file(in_file: UploadFile = File(...)):
    is_ok, dest_file = file_handler.upload_file(in_file)
    if not is_ok:
        raise HTTPException(
            status_code=400,
            detail="File type not allowed. Choose from"
            f" {file_handler._get_allowed_extensions()}",
        )
    print(f"{dest_file=}")
    uploaded_file = UploadedFile(path=dest_file)
    return uploaded_file

@app.post("/ocr", response_model=str)
def ocr_file(file_uri: str, actual_ocr_file: UploadFile = File(...)):
    if actual_ocr_file.content_type != "application/json":
        raise HTTPException("Actual OCR file must be a json file")
    ocr_result = file_handler.get_ocr_result(file_uri, actual_ocr_file)
    embeddings = file_handler.get_embeddings(ocr_result)
    date = ocr_result["createdDateTime"]
    print(date)
    return date


# def handle_upload_file(
#     upload_file: UploadFile, handler: Callable[[Path], None]
# ) -> None:
#     tmp_path = save_upload_file_tmp(upload_file)
#     try:
#         handler(tmp_path)  # Do something with the saved temp file
#     finally:
#         tmp_path.unlink()  # Delete the temp file


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
