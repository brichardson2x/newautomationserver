from fastapi import Depends, FastAPI, HTTPException, Header
from app.core.config import settings
from app.core.logging import setup_logging
from app.utils.generate_token import generate_token
from app.dependencies import read_security, get_settings