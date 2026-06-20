import shutil
from pathlib import Path

import freqtrade.rpc.api_server.web_ui as w

web_ui_path = Path(w.__file__)
src = web_ui_path.read_text()

if "/custom" in src:
    print("Custom dashboard already present")
else:
    # Copy dashboard HTML to freqtrade's ui directory
    ui_dir = web_ui_path.parent / "ui"
    shutil.copy(
        "/bot/dashboard/custom_dashboard.html",
        ui_dir / "custom_dashboard.html",
    )

    # Inject route before the catch-all route
    inject = '''

@router_ui.get("/custom")
async def custom_dashboard():
    return FileResponse(str(Path(__file__).parent / "ui/custom_dashboard.html"))

'''
    new_src = src.replace(
        '@router_ui.get("/{rest_of_path:path}")',
        inject + '@router_ui.get("/{rest_of_path:path}")',
    )
    web_ui_path.write_text(new_src)
    print("Custom dashboard route injected")
