from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
import re
from ruamel.yaml import YAML # type: ignore
from ruamel.yaml.comments import CommentedMap # type: ignore
from pathlib import Path
from typing import List, Set
from fastapi import FastAPI, HTTPException, Query, APIRouter, Body # type: ignore
import os
import subprocess
from pydantic import BaseModel, Field, ValidationError # type: ignore
from typing import Dict, List
from io import StringIO
from typing import Dict, Any
from app import write_yaml, read_yaml
dtb_config_router = APIRouter()

yaml = YAML()


#from bk import write_yaml
## api sua config thi chi can load default lên, và sửa thì gửi request sửa file và deploy thứ tự 3 câu lệnh à? hoặc deploy cả.
## neu co the thi ho tro socket luon, stream output bash lien tuc.
## nghien cuu xem 

##api 1: doc file conf
#api 2: doc file yamls
#sau do sua vao va chay lenh deploy thi dung chung duoc.

class MySQLConfig(BaseModel):
    expire_logs_days: int
    wait_timeout: int
    interactive_timeout: int
    innodb_log_file_size: str
    lower_case_table_names: int
    performance_schema: bool
    max_allowed_packet: str
    slow_query_log: bool
    open_files_limit: int
    plugin_load_add: str
    server_audit_logging: str
    server_audit_events: str | None = None
    server_audit_file_path: str | None = None
    server_audit_file_rotate_now: str | None = None
    server_audit_file_rotate_size: int | None = None
    server_audit_file_rotations: int | None = None

#ham doc gia tri
dtb_config_router("/gen_mysql_config")
def create_mysql_config(cfg: MySQLConfig, path_config: str = Query(...)):
    if path_config.__contains__("global"):
        write_yaml(path_config,vars(cfg))
    else:
        # if os.path.exists(path_config):
        #     return {"message": f"File đã tồn tại ở đường dẫn: {cfg.path}"}
        try:
            with open(path_config, "w") as f:
                f.write("[mysqld]\n")
                f.write(f"expire_logs_days = {cfg.expire_logs_days}\n")
                f.write(f"wait_timeout = {cfg.wait_timeout}\n")
                f.write(f"interactive_timeout = {cfg.interactive_timeout}\n")
                f.write(f"innodb_log_file_size = {cfg.innodb_log_file_size}\n")
                f.write(f"lower_case_table_names = {cfg.lower_case_table_names}\n")
                f.write(f"performance_schema = {str(cfg.performance_schema)}\n")
                f.write(f"max_allowed_packet = {cfg.max_allowed_packet}\n")
                f.write(f"slow_query_log = {str(cfg.slow_query_log)}\n")
                f.write(f"open_files_limit = {cfg.open_files_limit}\n")
                f.write(f"plugin_load_add = {cfg.plugin_load_add}\n")
                f.write(f"server_audit_logging = {cfg.server_audit_logging}\n")

                if cfg.server_audit_logging.upper() == "ON":
                    if not all([
                        cfg.server_audit_events,
                        cfg.server_audit_file_path,
                        cfg.server_audit_file_rotate_now,
                        cfg.server_audit_file_rotate_size is not None,
                        cfg.server_audit_file_rotations is not None
                    ]):
                        raise HTTPException(
                            status_code=400,
                            detail="Thiếu thông tin server_audit_* cần thiết khi server_audit_logging = ON"
                        )
                    f.write(f"server_audit_events = {cfg.server_audit_events}\n")
                    f.write(f"server_audit_file_path = {cfg.server_audit_file_path}\n")
                    f.write(f"server_audit_file_rotate_now = {cfg.server_audit_file_rotate_now}\n")
                    f.write(f"server_audit_file_rotate_size = {cfg.server_audit_file_rotate_size}\n")
                    f.write(f"server_audit_file_rotations = {cfg.server_audit_file_rotations}\n")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Lỗi khi ghi file: {str(e)}")

    return {"message": f"✅ Đã tạo file mới tại {cfg.path}"}

#ham doc gia tri
@dtb_config_router.get("/read_mysql_config")
def read_and_fill_mysql_config(file_path: str) -> dict:
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Không tìm thấy file ở đường dẫn: {file_path}")

    try:
        # Bước 1: Đọc file và lấy dict
        if "global" in file_path:
            with open(file_path, "r") as f:
                config_dict = yaml.safe_load(f) or {}
        else:
            config_dict = {}
            with open(file_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or line.startswith("["):
                        continue
                    if "=" in line:
                        key, value = line.split("=", 1)
                        config_dict[key.strip()] = value.strip()

        # Bước 2: Đưa vào Pydantic để chuẩn hóa + điền default
        cfg = MySQLConfig(**config_dict)
        return cfg.dict()
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=f"Lỗi dữ liệu đầu vào: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi xử lý file: {str(e)}")

def deploy_config():
    print("Neu chay lan luot thi the nao, chay lan 2 thi the nao")
