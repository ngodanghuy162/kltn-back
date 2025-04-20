##api chon duong dan -> hien thi cac ban backup cac ngay --> truyen vao ban backup moi nhat de restore. sua file bash, chon node backup
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
import re
from ruamel.yaml import YAML # type: ignore
from ruamel.yaml.comments import CommentedMap # type: ignore
from pathlib import Path
from typing import List, Set
from fastapi import FastAPI, HTTPException, Query, APIRouter

from io import StringIO
from typing import Dict, Any
restore_router = APIRouter()

yaml = YAML()

FILENAME_PATTERN = re.compile(r"mysqlbackup_(\d{2})_(\d{2})_(\d{4})\d*")
# re.compile(r"mysqlbackup_(\d{2}_\d{2}_\d{4}).*")


@restore_router.get(
    "/listbackup",
    summary="Lấy danh sách ngày backup từ tên file",
    response_description="Trả về danh sách các ngày theo định dạng DD-MM-YYYY từ tên file backup",
)
def list_backup_dates(
    path: str = Query(
        default="/Users/ngodanghuy/KLTN/test",  # bạn có thể đổi thành folder mặc định của bạn
        title="Đường dẫn thư mục backup",
        description="Đường dẫn chứa các file backup theo định dạng mysqlbackup_DD_MM_YYYY",
        example="/tmp/backup"
    )
):
    folder = Path(path)
    if not folder.exists() or not folder.is_dir():
        return {"error": "Invalid folder path"}

    backup_dates = []

    for file in folder.iterdir():
        # if file.is_file():
            match = FILENAME_PATTERN.match(file.name)
            if match:
                day, month, year = match.groups()
                backup_dates.append(f"{day}-{month}-{year}")
    return {"dates": backup_dates}


#api truyen ngay vao, lay file do sua vao file bash hoac khai bao moi truong xong chay file bash