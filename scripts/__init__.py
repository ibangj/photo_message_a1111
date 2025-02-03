import os
import sys
import gradio as gr
import json
import base64
import traceback
from datetime import datetime
from modules import script_callbacks, shared, api, scripts, img2img
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import io
from PIL import Image
import pandas as pd
import numpy as np

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

def update_photo_list():
    photo_data = [[p.timestamp, p.name, p.message] for p in photos]
    print(f"[Photo Message] Updating photo list with {len(photo_data)} photos")
    # Convert to DataFrame
    df = pd.DataFrame(photo_data, columns=["Time", "Name", "Message"])
    return df

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
                    # Initialize with DataFrame
                    initial_df = pd.DataFrame([[p.timestamp, p.name, p.message] for p in photos], 
                                           columns=["Time", "Name", "Message"])
                    photo_list = gr.Dataframe(
                        headers=["Time", "Name", "Message"],
                        row_count=10,
                        col_count=(3, "fixed"),
                        interactive=True,
                        elem_id="photo_list",
                        value=initial_df
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
                    status_text = gr.Textbox(label="Status", interactive=False, value="No image selected")
            
            def on_select(evt: gr.SelectData, current_value):
                try:
                    print(f"[Photo Message] Selection event: {evt.index}")
                    print(f"[Photo Message] Current dataframe value:\n{current_value}")
                    
                    # Check if we have any data
                    if current_value is None or len(current_value.index) == 0:
                        print("[Photo Message] No data in DataFrame")
                        return None
                        
                    # Get the selected row using iloc
                    try:
                        row_idx = evt.index[0]
                        if row_idx >= len(current_value.index):
                            print("[Photo Message] Selected index out of range")
                            return None
                            
                        # Get timestamp from the first column
                        timestamp = current_value.iloc[row_idx, 0]  # Get first column value
                        print(f"[Photo Message] Selected timestamp: {timestamp}")
                        
                        # Debug the photos list
                        print(f"[Photo Message] Current photos in memory: {len(photos)}")
                        for p in photos:
                            print(f"[Photo Message] Stored photo: {p.timestamp}, {p.name}")
                        
                        # Get and return the image
                        image = get_photo_by_timestamp(timestamp)
                        if image is not None:
                            print("[Photo Message] Successfully loaded image")
                            return image
                        else:
                            print("[Photo Message] Failed to load image")
                            return None
                            
                    except IndexError as ie:
                        print(f"[Photo Message] Index error: {ie}")
                        return None
                    
                except Exception as e:
                    print(f"[Photo Message] Error selecting photo: {e}")
                    print(traceback.format_exc())
                    return None
            
            def send_to_img2img_tab(image):
                if image is not None:
                    try:
                        print("[Photo Message] Attempting to send image to img2img...")
                        
                        # Convert PIL Image to numpy array
                        img_array = np.array(image)
                        
                        # Try to set the image using the img2img module directly
                        try:
                            import modules.img2img as img2img_module
                            if hasattr(img2img_module, 'init_img'):
                                print("[Photo Message] Setting image via img2img module...")
                                img2img_module.init_img = img_array
                                return "Image sent to img2img tab. Please switch to img2img tab."
                        except Exception as e:
                            print(f"[Photo Message] Error setting via img2img module: {e}")
                        
                        # Fallback: Try to set via shared state
                        try:
                            if hasattr(shared.state, 'img2img_image'):
                                print("[Photo Message] Setting image via shared state...")
                                shared.state.img2img_image = img_array
                                return "Image sent to img2img tab. Please switch to img2img tab."
                        except Exception as e:
                            print(f"[Photo Message] Error setting via shared state: {e}")
                        
                        return "Could not send image to img2img. Please try copying and pasting manually."
                    except Exception as e:
                        print(f"[Photo Message] Error sending to img2img: {e}")
                        print(traceback.format_exc())
                        return f"Error: {str(e)}"
                return "No image selected"

            def send_to_txt2img_tab(image):
                if image is not None:
                    try:
                        print("[Photo Message] Attempting to send image to ControlNet...")
                        
                        # Convert PIL Image to numpy array
                        img_array = np.array(image)
                        
                        # Try to find ControlNet in the scripts
                        found = False
                        
                        # Method 1: Try through scripts collection
                        try:
                            print("[Photo Message] Searching for ControlNet in scripts...")
                            for script in scripts.scripts_txt2img.alwayson_scripts:
                                if hasattr(script, 'title') and callable(script.title):
                                    script_title = script.title().lower()
                                    print(f"[Photo Message] Found script: {script_title}")
                                    if "controlnet" in script_title:
                                        print("[Photo Message] Found ControlNet script")
                                        if hasattr(script, 'set_input_image'):
                                            script.set_input_image(img_array)
                                            found = True
                                            print("[Photo Message] Set image using set_input_image")
                                            break
                        except Exception as e:
                            print(f"[Photo Message] Error searching scripts: {e}")
                            print(traceback.format_exc())
                        
                        # Method 2: Try through extension modules
                        if not found:
                            try:
                                print("[Photo Message] Trying to import ControlNet module...")
                                import importlib
                                controlnet = importlib.import_module('extensions.sd-webui-controlnet.scripts.controlnet')
                                if hasattr(controlnet, 'update_input_image'):
                                    controlnet.update_input_image(img_array)
                                    found = True
                                    print("[Photo Message] Set image through ControlNet module")
                            except Exception as e:
                                print(f"[Photo Message] Error importing ControlNet module: {e}")
                        
                        if found:
                            return "Image sent to ControlNet. Please switch to txt2img tab and check ControlNet panel."
                        else:
                            return "Could not find ControlNet. Please make sure ControlNet extension is installed and enabled."
                            
                    except Exception as e:
                        print(f"[Photo Message] Error sending to ControlNet: {e}")
                        print(traceback.format_exc())
                        return f"Error: {str(e)}"
                return "No image selected"
            
            # Wire up the events
            refresh_btn.click(update_photo_list, outputs=[photo_list])
            photo_list.select(on_select, inputs=[photo_list], outputs=[preview_image])
            send_to_img2img.click(send_to_img2img_tab, inputs=[preview_image], outputs=[status_text])
            send_to_txt2img.click(send_to_txt2img_tab, inputs=[preview_image], outputs=[status_text])
            
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