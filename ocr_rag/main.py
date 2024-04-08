import os
import uvicorn
import traceback
from fastapi import FastAPI, File, UploadFile, HTTPException

from ocr_rag.utils import (
    FileHandler,
    EmbeddingHandler,
    UploadedFile,
    QueryResponse,
    get_cfg,
)

app = FastAPI()

cur_dir = os.path.abspath(os.path.dirname(__file__))
cfg_path = os.path.join(os.path.dirname(cur_dir), "cfg.yaml")
cfg = get_cfg(cfg_path)
file_handler = FileHandler(cfg["file_handler"])
embedding_handler = EmbeddingHandler(cfg["embedding_handler"])


@app.post("/upload", response_model=UploadedFile)
def upload(in_file: UploadFile = File(...)):
    """
    Uploads the file to a (local) bucket. File type can be pdf or image.
    """
    is_ok, uploaded_file = file_handler.upload_file(in_file)
    if not is_ok:
        raise HTTPException(
            status_code=400,
            detail="File type not allowed. Choose from"
            f" {file_handler._get_allowed_extensions()}",
        )
    return uploaded_file


@app.post("/ocr", response_model=bool)
def ocr(
    file_uuid: str, actual_ocr_file: UploadFile = File(...), do_translate: bool = True
):
    """
    Create embeddings for the given uuid related file.
    - **file_uuid**: UUID of the file as returned from the *upload* endpoint
    - **actual_ocr_file**: json file with the actual OCR result
    """
    if actual_ocr_file.content_type != "application/json":
        raise HTTPException(
            status_code=400, detail="Actual OCR file must be a json file"
        )
    try:
        ocr_result = file_handler.get_ocr_result(file_uuid, actual_ocr_file)
        embedding_handler.create_embeddings(file_uuid, ocr_result)
        if do_translate:
            ocr_result = file_handler.get_ocr_result(
                file_uuid, actual_ocr_file, do_translate=do_translate
            )
            embedding_handler.create_embeddings(
                file_uuid, ocr_result, do_translate=do_translate
            )
    except:
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500, detail="Something went wrong with the file parsing"
        )
    return True


@app.delete("/ocr")
def ocr_delete(file_uuid: str):
    embedding_handler.remove_embeddings(file_uuid)


@app.post("/exctract", response_model=QueryResponse)
def exctract(file_uuid: str, query: str, do_translate: bool = True):
    """
    Given a file UUID (or list of UUIDs comma separated) and a query
    retrieves the most relevant parts of the specified files and returns a response
    based on this information
    - **file_uuid**: (comma separated) UUID(s) of the related files
    - **query**: Query/question to be answered.
    """
    response = embedding_handler.get_response_with_rag(
        file_uuid, query, do_translate=do_translate
    )
    return response


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
