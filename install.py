import launch

if not launch.is_installed("aiohttp"):
    launch.run_pip("install aiohttp", "requirements for photo message extension") 