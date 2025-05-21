#!/usr/bin/env python
import sys
import os
import uvicorn

# パスを追加して myrdal モジュールを見つけられるようにする
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
