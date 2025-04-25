# app.py
from pydantic import BaseModel # type: ignore
from routers import bk , deploy, dtbconfig, restore
import asyncio
import subprocess
import json
from ruamel.yaml import YAML # type: ignore
from ruamel.yaml.comments import CommentedMap # type: ignore
from fastapi import FastAPI, Query, Body, HTTPException, Response, Path, WebSocket,HTTPException # type: ignore
from pathlib import Path
from io import StringIO
from typing import Dict, Any
from fastapi.middleware.cors import CORSMiddleware # type: ignore


import os
#import yaml
import subprocess

yaml = YAML()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 👈 Cho phép frontend truy cập
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(bk.bk_router)
app.include_router(restore.restore_router)
app.include_router(dtbconfig.dtb_config_router)

arr = [1,2,3,4,5]

@app.get("/")
async def root():
    return { "message": "Hello world" }

def read_yaml(path):
    """Đọc file YAML"""
    try:
        with open(path, "r") as file:
            return yaml.load(file)  # Load YAML thành Python dict
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File YAML không tồn tại")
    except yaml.YAMLError as e:
        raise HTTPException(status_code=400, detail=f"Lỗi YAML: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def write_yaml(path,dict_update):
    try:
        # Đọc dữ liệu YAML hiện tại
        with open(path, "r") as file:
            data = yaml.load(file) or {}  # Tránh lỗi nếu file rỗng
        
        # Cập nhật dữ liệu
        for key, value in dict_update.items():
            data[key] = value

        print("Dữ liệu cũ:", data)

        # Ghi lại file
        with open(path, "w") as file:
            yaml.dump(data, file)

        return {"message": "Cập nhật YAML thành công!"}

    except Exception as e:
        return {"error": str(e)}

###
#  api1. api gui render file all2.yml
# api2. api gui de sua noi dung file yaml
# api 3: api de chon folder backup trong may ubuntu
# api 4:  api chay file bash va cho ket qua
# api 5: xem trang thai log phuc hoi lich su cum cluster mariadb -> dung grafana roi

@app.get("/cat")
async def cat_file(path :str):
    try:
        result = subprocess.run(["cat", path], capture_output=True, text=True)
        return Response(content=result.stdout, media_type="text/plain")
    except Exception as e:
        return {"error": str(e)}

@app.get("/ls")
async def cat_file(path :str):
    try:
        result = subprocess.run(["ls", path], capture_output=True, text=True)
        return Response(content=result.stdout, media_type="text/plain")
    except Exception as e:
        return {"error": str(e)}

#api doc file yaml
@app.get("/readfile")
async def get_yaml_content(
    path: str = Query("/Users/ngodanghuy/KLTN/back/kltn-back/all2.yml", description="Đường dẫn file YAML cần đọc")
):
    """API đọc file YAML và trả về nội dung"""
    content = read_yaml(path) # Đọc YAML ra dict
    yaml_string = StringIO()
    yaml.dump(content, yaml_string)  # ruamel.yaml không dùng default_flow_style=False
    return Response(content=yaml_string.getvalue(), media_type="text/plain")

##get one key
@app.get("/readkey")
async def get_yaml_content(
    key: str = Query("kolla_internal_vip_address", description="Đường dẫn file YAML cần đọc")
):
    """API đọc file YAML và trả về nội dung"""
    content = read_yaml("/Users/ngodanghuy/KLTN/back/kltn-back/all2.yml") # Đọc YAML ra dict
    data = content[key]
    return Response(content=data, media_type="text/plain")

#api tesst update
@app.get("/test")
async def tesst_update():
    test_dict = {"enable_haproxy": "bi mat", "kolla_internal_vip_address" : "1.2.3.4"}
    write_yaml("/Users/ngodanghuy/KLTN/back/kltn-back/all2.yml",test_dict) 
    return Response(content="Done", media_type="text/plain")


#api lay thu muc hien tai
@app.get("/pwd")
async def pwd():
    try:
        result = subprocess.run(["pwd"], capture_output=True, text=True)
        return Response(content=result.stdout, media_type="text/plain")
    except Exception as e:
        return {"error": str(e)}
    
#api chay file bash
@app.post("/bash")
async def pwd(cmd:str):
    try:
        result = subprocess.Popen(cmd, shell=True, capture_output=True, text=True)
        return Response(content=result.stdout, media_type="text/plain")
    except Exception as e:
        return {"error": str(e)}
    
#api update file
@app.post("/update")
async def update_config(
    path: str = Query("/Users/ngodanghuy/KLTN/back/all2.yml", description="Đường dẫn file YAML cần cập nhật"),
    config: Dict[str, Any] = Body(...)
):
    return write_yaml(path, config)

#api chon file
@app.get("/browse")
async def browse_files(
    path: str = Query(None, description="Đường dẫn thư mục cần duyệt")
):
    """API duyệt file & folder giống chọn file upload"""
    try:
        # Nếu không có path, mặc định lấy thư mục root
        if path is None:
            path = "/"

        # Chuyển về đường dẫn tuyệt đối
        path_obj = Path(path).resolve()

        # Kiểm tra xem thư mục có tồn tại không
        if not path_obj.exists() or not path_obj.is_dir():
            raise HTTPException(status_code=400, detail="Thư mục không tồn tại hoặc không hợp lệ")

        # Lấy danh sách file/folder trong thư mục
        items = [
            {"name": f.name, "path": str(f.resolve()), "type": "folder" if f.is_dir() else "file"}
            for f in path_obj.iterdir()
        ]
        return {"current_path": str(path_obj), "items": items}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/run_bash")
async def run_bash_script(websocket: WebSocket):
    await websocket.accept()

    # Nhận đường dẫn file Bash từ frontend
    data = await websocket.receive_text()
    try:
        request_data = json.loads(data)  # Chuyển JSON thành dict
        script_path = request_data.get("path", "")

        if not script_path:
            await websocket.send_text("Error: Missing script path")
            await websocket.close()
            return

        # Chạy file Bash
        process = await asyncio.create_subprocess_exec(
            "bash", script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )

        while True:
            line = await process.stdout.readline()
            if not line:
                break
            await websocket.send_text(line.decode().strip())  # Gửi output từng dòng

        await websocket.close()

    except Exception as e:
        await websocket.send_text(f"Error: {str(e)}")
        await websocket.close()

class CronJob(BaseModel):
    cron: str

@app.post("/set-cron")
def set_cron(job: CronJob):
    cron_command = f"(crontab -l 2>/dev/null; echo '{job.cron} /path/to/script.sh') | crontab -"
    try:
        subprocess.run(cron_command, shell=True, check=True)
        return {"message": "Crontab set successfully", "cron": job.cron}
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=500, detail="Failed to set crontab")