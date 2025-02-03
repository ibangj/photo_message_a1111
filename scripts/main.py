import gradio as gr
import json
import base64
import traceback
from datetime import datetime
from modules import script_callbacks
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

print("[Photo Message] Loading extension...")

# Store received photos
photos = []

class PhotoMessage:
    def __init__(self, image_data, name, message, timestamp):
        self.image_data = image_data
        self.name = name
        self.message = message
        self.timestamp = timestamp

class PhotoRequest(BaseModel):
    image: str
    name: str
    message: str
    display_app_url: str | None = None

def on_app_started(demo: FastAPI):
    print("[Photo Message] Registering API endpoint...")
    try:
        @demo.post("/sdapi/v1/photo_message/receive")
        async def receive_photo(data: PhotoRequest):
            try:
                print(f"[Photo Message] Received request from {data.name}")
                print(f"[Photo Message] Message: {data.message}")
                
                # Create new photo message
                photo = PhotoMessage(
                    image_data=data.image,
                    name=data.name,
                    message=data.message,
                    timestamp=datetime.now().isoformat()
                )
                
                # Add to queue
                photos.append(photo)
                print(f"[Photo Message] Added photo to queue. Total photos: {len(photos)}")
                
                return {
                    "status": "success", 
                    "message": f"Photo received from {data.name}",
                    "timestamp": photo.timestamp
                }
            except Exception as e:
                print(f"[Photo Message] Error processing request: {str(e)}")
                print(traceback.format_exc())
                raise HTTPException(status_code=500, detail=str(e))
                
        print("[Photo Message] API endpoint registered successfully")
        print(f"[Photo Message] Available routes: {[route.path for route in demo.routes]}")
        
    except Exception as e:
        print(f"[Photo Message] Error registering API endpoint: {str(e)}")
        print(traceback.format_exc())

# Register the API endpoint
script_callbacks.on_app_started(on_app_started)

def on_ui_tabs():
    try:
        print("[Photo Message] Creating UI tab...")
        with gr.Blocks(analytics_enabled=False) as photo_message_tab:
            gr.Markdown("# Photo Message Extension")
            gr.Markdown("Received photos will appear here.")
            
            with gr.Row():
                photo_list = gr.Dataframe(
                    headers=["Time", "Name", "Message"],
                    row_count=10,
                    col_count=(3, "fixed"),
                    interactive=False
                )
                refresh_btn = gr.Button("🔄 Refresh")
            
            def update_photo_list():
                return [[p.timestamp, p.name, p.message] for p in photos]
            
            refresh_btn.click(update_photo_list, outputs=[photo_list])
            photo_list.value = update_photo_list()
            
        print("[Photo Message] UI tab created successfully")
        return [(photo_message_tab, "Photo Message", "photo_message_a1111")]
    except Exception as e:
        print(f"[Photo Message] Error creating UI tab: {str(e)}")
        print(traceback.format_exc())
        return []

# Register the UI tab
script_callbacks.on_ui_tabs(on_ui_tabs)
print("[Photo Message] Extension initialization completed") 