from __future__ import annotations

from mangum import Mangum

from app.main import app

lambda_handler = Mangum(app)
