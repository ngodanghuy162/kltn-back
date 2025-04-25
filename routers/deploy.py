## sua cac bien var, xong chay cau lenh deploy :>
# la chay file bash.
import asyncio
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
import re
from ruamel.yaml import YAML # type: ignore
from ruamel.yaml.comments import CommentedMap # type: ignore
from pathlib import Path
from typing import List, Set
from fastapi import FastAPI, HTTPException, Query, APIRouter, Body # type: ignore
from fastapi.responses import StreamingResponse # type: ignore
import os
import subprocess
from pydantic import BaseModel, Field, ValidationError # type: ignore
from typing import Dict, List
from io import StringIO
from typing import Dict, Any
from general import write_yaml, read_yaml, update_ansible_inventory
deploy_router = APIRouter()

yaml = YAML()

#api trien khai 1 node: Sua inventory, chay deploy
#3 node: sua inventory, chay deploy
##3 node kem haproxy: Sua inventory 2 group, sua ip vip, deploy :>

