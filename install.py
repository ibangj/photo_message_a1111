import launch

if not launch.is_installed("aiohttp"):
    launch.run_pip("install aiohttp", "requirements for photo message extension")

if not launch.is_installed("fastapi"):
    launch.run_pip("install fastapi", "requirements for photo message extension")

if not launch.is_installed("pydantic"):
    launch.run_pip("install pydantic", "requirements for photo message extension")

if not launch.is_installed("pillow"):
    launch.run_pip("install pillow", "requirements for photo message extension")

if not launch.is_installed("python-socketio"):
    launch.run_pip("install python-socketio", "requirements for photo message extension")

if not launch.is_installed("gradio"):
    launch.run_pip("install gradio", "requirements for photo message extension") 