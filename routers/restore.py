##api chon duong dan -> hien thi cac ban backup cac ngay --> truyen vao ban backup moi nhat de restore. sua file bash, chon node backup
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
import re
from ruamel.yaml import YAML # type: ignore
from ruamel.yaml.comments import CommentedMap # type: ignore
from pathlib import Path
from typing import List, Set
from fastapi import FastAPI, HTTPException, Query, APIRouter, Body
import os
from pydantic import BaseModel, Field
from typing import Dict, List
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

# --- Pydantic Model cho Request Body ---
class ShUpdateRequest(BaseModel):
    file_path: str = Field(..., description="Đường dẫn đầy đủ đến file .sh cần sửa.")
    updates: Dict[str, str] = Field(..., description="Dictionary chứa các biến cần cập nhật và giá trị mới. Ví dụ: {'VAR_A': 'new_value_1', 'ANOTHER_VAR': 'hello world'}")

# --- Khởi tạo FastAPI App ---
app = FastAPI(
    title="Shell Script Variable Updater API",
    description="API để đọc và cập nhật biến trong file .sh",
)

# --- Hàm xử lý logic cập nhật file ---
def update_shell_variables(file_path: str, updates: Dict[str, str]) -> bool:
    """
    Đọc file shell script, cập nhật các biến được chỉ định và ghi lại file.

    Args:
        file_path: Đường dẫn đến file .sh.
        updates: Dict các biến và giá trị mới.

    Returns:
        True nếu thành công, False nếu có lỗi đọc/ghi file.

    Raises:
        FileNotFoundError: Nếu file không tồn tại.
        IOError: Nếu có lỗi khi ghi file.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File không tồn tại: {file_path}")
    if not os.path.isfile(file_path):
         raise ValueError(f"Đường dẫn không phải là file: {file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Lỗi khi đọc file {file_path}: {e}")
        # Hoặc raise một Exception cụ thể hơn nếu muốn FastAPI bắt và trả lỗi 500
        raise IOError(f"Không thể đọc file: {file_path}") from e


    new_lines = []
    updated_keys = set() # Theo dõi các key đã được cập nhật trong file

    # Regex để tìm các dòng khai báo biến dạng: VAR_NAME=value hoặc VAR_NAME="value" hoặc export VAR_NAME=...
    # Nó sẽ bắt tên biến vào group 1
    # Lưu ý: Regex này khá cơ bản, có thể không xử lý được các trường hợp phức tạp
    # (ví dụ: khai báo nhiều biến trên 1 dòng, comment phức tạp, giá trị nhiều dòng...)
    var_pattern = re.compile(r"^\s*(?:export\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*=(.*)")
    #                                          ^^ optional export  ^^^^^^^^^^^ var name ^^^^^^ =value...

    for line in lines:
        match = var_pattern.match(line)
        original_line = line # Giữ lại dòng gốc để dùng nếu không cập nhật

        if match:
            var_name = match.group(1)
            if var_name in updates:
                new_value = updates[var_name]
                # Tạo dòng mới. Quyết định có đặt trong dấu ngoặc kép hay không.
                # Cách đơn giản: luôn đặt trong dấu ngoặc kép để xử lý các giá trị có khoảng trắng.
                # Cảnh báo: Điều này có thể thay đổi cách script hoạt động nếu giá trị gốc không có dấu ngoặc kép
                # và script phụ thuộc vào việc đó (ví dụ: value là một lệnh khác).
                # Nếu cần giữ nguyên kiểu dấu ngoặc gốc thì logic sẽ phức tạp hơn nhiều.
                new_line = f'{var_name}="{new_value}"\n'
                new_lines.append(new_line)
                updated_keys.add(var_name)
                continue # Chuyển sang dòng tiếp theo sau khi cập nhật

        # Nếu dòng không khớp regex hoặc khớp nhưng không cần update, giữ nguyên dòng gốc
        new_lines.append(original_line)

    # Kiểm tra xem có biến nào trong `updates` mà không tìm thấy trong file không
    # Tùy chọn: bạn có thể muốn báo lỗi hoặc bỏ qua
    missing_keys = set(updates.keys()) - updated_keys
    if missing_keys:
        print(f"Cảnh báo: Không tìm thấy các biến sau trong file để cập nhật: {missing_keys}")
        # Hoặc bạn có thể raise Exception ở đây nếu muốn việc thiếu key là lỗi nghiêm trọng

    # Ghi lại nội dung mới vào file (ghi đè)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        return True # Trả về True nếu ghi thành công
    except Exception as e:
        print(f"Lỗi khi ghi file {file_path}: {e}")
        raise IOError(f"Không thể ghi file: {file_path}") from e


# --- API Endpoint ---
@app.post("/update-sh-vars/", summary="Cập nhật biến trong file Shell Script")
async def update_sh_vars_endpoint(request_data: ShUpdateRequest):
    """
    Endpoint để nhận đường dẫn file .sh và danh sách các biến cần cập nhật.
    Nó sẽ đọc file, sửa các giá trị biến và ghi đè lại file gốc.

    **Cảnh báo:** Sử dụng cẩn thận, chỉ định đường dẫn file đáng tin cậy.
    """
    try:
        success = update_shell_variables(request_data.file_path, request_data.updates)
        if success:
            return {"status": "success", "message": f"File '{request_data.file_path}' đã được cập nhật thành công."}
        else:
            # Trường hợp này ít khi xảy ra nếu không có exception, nhưng để phòng ngừa
             raise HTTPException(status_code=500, detail="Cập nhật file thất bại mà không rõ lý do.")

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e: # Bắt lỗi nếu đường dẫn không phải file
        raise HTTPException(status_code=400, detail=str(e))
    except IOError as e: # Bắt lỗi đọc/ghi file
        raise HTTPException(status_code=500, detail=f"Lỗi I/O: {e}")
    except Exception as e:
        # Bắt các lỗi không mong muốn khác
        print(f"Lỗi không xác định: {e}")
        raise HTTPException(status_code=500, detail=f"Lỗi server không xác định: {e}")

# --- Chạy server (nếu chạy trực tiếp file này) ---
if __name__ == "__main__":
    import uvicorn
    # Chạy server trên localhost, port 8000
    # reload=True sẽ tự động khởi động lại server khi code thay đổi (chỉ dùng khi dev)
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)