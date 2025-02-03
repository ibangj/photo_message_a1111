import os
import sys
import gradio as gr
import json
import base64
import traceback
from datetime import datetime
from modules import script_callbacks, shared, api
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import io
from PIL import Image

print("\n[Photo Message] ====== Extension Loading ======")
print(f"[Photo Message] Current directory: {os.path.dirname(os.path.abspath(__file__))}")
print(f"[Photo Message] Python path: {sys.path}")

# Store received photos
photos = []

class PhotoMessage:
    def __init__(self, image_data, name, message, timestamp):
        self.image_data = image_data  # Base64 encoded image data
        self.name = name
        self.message = message
        self.timestamp = timestamp

class PhotoRequest(BaseModel):
    image: str
    name: str
    message: str
    display_app_url: str | None = None

def api_only(app: FastAPI):
    """Register API endpoints only"""
    print("\n[Photo Message] Registering API endpoints...")
    print(f"[Photo Message] FastAPI app info: {app}")
    
    try:
        @app.get("/sdapi/v1/photo_message/ping")
        async def ping(request: Request):
            print(f"[Photo Message] Ping request received")
            print(f"[Photo Message] Request base URL: {request.base_url}")
            print(f"[Photo Message] Request headers: {request.headers}")
            print(f"[Photo Message] Request client: {request.client}")
            return {
                "status": "ok", 
                "message": "Photo Message extension is alive!",
                "base_url": str(request.base_url),
                "url": str(request.url),
                "client": str(request.client)
            }
            
        print("[Photo Message] Registered ping endpoint")
        
        @app.get("/sdapi/v1/photo_message/test")
        async def test(request: Request):
            print(f"[Photo Message] Test request received from: {request.client}")
            return {
                "status": "success", 
                "message": "Photo Message extension is working!",
                "client": str(request.client)
            }
            
        print("[Photo Message] Registered test endpoint")
        
        @app.post("/sdapi/v1/photo_message/receive")
        async def receive_photo(data: PhotoRequest, request: Request):
            print(f"[Photo Message] Receive endpoint hit from: {request.client}")
            print(f"[Photo Message] Request data: name={data.name}, message={data.message}")
            
            try:
                photo = PhotoMessage(
                    image_data=data.image,
                    name=data.name,
                    message=data.message,
                    timestamp=datetime.now().isoformat()
                )
                photos.append(photo)
                print(f"[Photo Message] Added photo to queue. Total photos: {len(photos)}")
                
                return {
                    "status": "success", 
                    "message": f"Photo received from {data.name}",
                    "timestamp": photo.timestamp,
                    "client": str(request.client)
                }
            except Exception as e:
                error_msg = f"Error processing request: {str(e)}"
                print(f"[Photo Message] {error_msg}")
                print(traceback.format_exc())
                raise HTTPException(status_code=500, detail=error_msg)
                
        print("[Photo Message] Registered receive endpoint")
        
    except Exception as e:
        print(f"[Photo Message] Error registering endpoints: {str(e)}")
        print(traceback.format_exc())

def on_app_started(demo: gr.Blocks, app: FastAPI):
    """Main callback when the app starts"""
    print("\n[Photo Message] App started callback triggered")
    print(f"[Photo Message] Gradio Blocks type: {type(demo)}")
    print(f"[Photo Message] FastAPI app type: {type(app)}")
    
    if app is None:
        print("[Photo Message] Error: FastAPI app is None!")
        return
        
    if not isinstance(app, FastAPI):
        print(f"[Photo Message] Error: Expected FastAPI app, got {type(app)}")
        return
    
    try:
        # Register API endpoints using the FastAPI app
        api_only(app)
        print("[Photo Message] API registration completed")
    except Exception as e:
        print(f"[Photo Message] Error in app_started: {str(e)}")
        print(traceback.format_exc())

def get_photo_by_timestamp(timestamp):
    for photo in photos:
        if photo.timestamp == timestamp:
            try:
                # Convert base64 to image data
                image_bytes = base64.b64decode(photo.image_data)
                # Create a PIL Image from bytes
                image = Image.open(io.BytesIO(image_bytes))
                return image
            except Exception as e:
                print(f"Error decoding image: {e}")
                print(traceback.format_exc())
                return None
    return None

def on_ui_tabs():
    """Register UI components"""
    try:
        print("\n[Photo Message] Creating UI tab...")
        with gr.Blocks(analytics_enabled=False) as photo_message_tab:
            gr.Markdown("# Photo Message Extension")
            gr.Markdown("Received photos will appear here.")
            
            with gr.Row():
                # Left column for the list
                with gr.Column(scale=2):
                    photo_list = gr.Dataframe(
                        headers=["Time", "Name", "Message"],
                        row_count=10,
                        col_count=(3, "fixed"),
                        interactive=True,
                        elem_id="photo_list"
                    )
                    refresh_btn = gr.Button("🔄", size="sm")
                
                # Right column for image preview and actions
                with gr.Column(scale=3):
                    preview_image = gr.Image(
                        label="Selected Photo",
                        show_label=True,
                        interactive=False,
                        type="pil",
                        height=400
                    )
                    with gr.Row():
                        send_to_img2img = gr.Button("Send to img2img", variant="primary")
                        send_to_txt2img = gr.Button("Use as ControlNet input", variant="primary")
                    status_text = gr.Textbox(label="Status", interactive=False)
            
            def update_photo_list():
                return [[p.timestamp, p.name, p.message] for p in photos]
            
            def on_select(evt: gr.SelectData):
                try:
                    print(f"[Photo Message] Selection event: {evt.index}")
                    timestamp = photo_list.value[evt.index[0]][0]
                    print(f"[Photo Message] Selected timestamp: {timestamp}")
                    image = get_photo_by_timestamp(timestamp)
                    if image is not None:
                        print("[Photo Message] Successfully loaded image")
                        return image
                    else:
                        print("[Photo Message] Failed to load image")
                except Exception as e:
                    print(f"[Photo Message] Error selecting photo: {e}")
                    print(traceback.format_exc())
                return None
            
            def send_to_img2img_tab(image):
                if image is not None:
                    try:
                        # Convert PIL Image to bytes
                        img_byte_arr = io.BytesIO()
                        image.save(img_byte_arr, format='PNG')
                        img_bytes = img_byte_arr.getvalue()
                        
                        # Set the image in img2img tab
                        shared.state.img2img_image = img_bytes
                        return "Image sent to img2img tab. Please switch to img2img tab."
                    except Exception as e:
                        print(f"[Photo Message] Error sending to img2img: {e}")
                        print(traceback.format_exc())
                        return f"Error: {str(e)}"
                return "No image selected"

            def send_to_txt2img_tab(image):
                if image is not None:
                    try:
                        # Convert PIL Image to bytes
                        img_byte_arr = io.BytesIO()
                        image.save(img_byte_arr, format='PNG')
                        img_bytes = img_byte_arr.getvalue()
                        
                        # TODO: Implement ControlNet integration
                        # This would need to be implemented based on how ControlNet accepts images
                        return "Image sent to ControlNet. Please switch to txt2img tab and enable ControlNet."
                    except Exception as e:
                        print(f"[Photo Message] Error sending to ControlNet: {e}")
                        print(traceback.format_exc())
                        return f"Error: {str(e)}"
                return "No image selected"
            
            # Wire up the events
            refresh_btn.click(update_photo_list, outputs=[photo_list])
            photo_list.select(on_select, outputs=[preview_image])
            send_to_img2img.click(send_to_img2img_tab, inputs=[preview_image], outputs=[status_text])
            send_to_txt2img.click(send_to_txt2img_tab, inputs=[preview_image], outputs=[status_text])
            
            # Initialize the list
            photo_list.value = update_photo_list()
            
        print("[Photo Message] UI tab created successfully")
        return [(photo_message_tab, "Photo Message", "photo_message_a1111")]
    except Exception as e:
        print(f"[Photo Message] Error creating UI tab: {str(e)}")
        print(traceback.format_exc())
        return []

print("\n[Photo Message] Registering callbacks...")

# Register callbacks
script_callbacks.on_app_started(on_app_started)
script_callbacks.on_ui_tabs(on_ui_tabs)

print("[Photo Message] Extension initialization completed") 