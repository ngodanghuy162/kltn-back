from fastapi import APIRouter, Query # type: ignore
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
dtb_config_router = APIRouter()

yaml = YAML()

from bk import write_yaml
