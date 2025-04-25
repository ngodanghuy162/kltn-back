
from ruamel.yaml import YAML # type: ignore
from ruamel.yaml.comments import CommentedMap # type: ignore

yaml = YAML()


def read_yaml(path):
    """Đọc file YAML"""
    try:
        with open(path, "r") as file:
            return yaml.load(file)  # Load YAML thành Python dict
    except Exception as e:
        return {"error": str(e)}

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
