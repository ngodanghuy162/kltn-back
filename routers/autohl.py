from fastapi import APIRouter, Query , HTTPException# type: ignore
from configparser import ConfigParser
import os
from datetime import datetime
from pathlib import Path
import shutil
import subprocess
import re
from ruamel.yaml import YAML # type: ignore
from ruamel.yaml.comments import CommentedMap # type: ignore
from pydantic import BaseModel # type: ignore
from typing import List
from pathlib import Path
from io import StringIO
from typing import Dict, Any
from fastapi.responses import JSONResponse # type: ignore
from general import write_yaml, read_yaml, update_ansible_inventory, get_hosts_by_group, update_bash_file_vars, read_bash_file_var_for_bk_dump, update_bash_vars_for_mariabk ,RequestKollaBackup, RequestMySQLDump, RequestCrontab
from .bk import parse_crontab_to_str, update_crontab, parse_crontab_to_get_path
autohl_router = APIRouter()

yaml = YAML()

@autohl_router.get("/autohl/get_crontab")
async def get_crontab_auto_hl():
    schedule = parse_crontab_to_str(keyword="auto")
    script_path = parse_crontab_to_get_path(keyword="auto")
    return {
        "schedule": schedule,
        "script_path": script_path
    }

@autohl_router.post("/autohl/update_crontab")
async def update_crontab_for_auto_hl(data: RequestCrontab):
    return update_crontab(
        cron_schedule=data.cron_schedule, 
        cron_command=data.cron_command,
        keyword="auto",
        is_enable=data.is_enable
    )

