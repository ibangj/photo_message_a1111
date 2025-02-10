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
import requests
import time
import socketio

print("\n[Photo Message] ====== Extension Loading ======")
print(f"[Photo Message] Current directory: {os.path.dirname(os.path.abspath(__file__))}")
print(f"[Photo Message] Python path: {sys.path}")

# Initialize SocketIO client
sio = socketio.Client()

@sio.event
def connect():
    print("[Photo Message] Connected to display app")

@sio.event
def disconnect():
    print("[Photo Message] Disconnected from display app")

# Try to connect to display app
try:
    sio.connect('http://localhost:5001')
except Exception as e:
    print(f"[Photo Message] Could not connect to display app: {e}")

# JavaScript code for handling tab switching and image sending
js_code = """
function gradioApp() {
    const elems = document.getElementsByTagName('gradio-app');
    const elem = elems.length == 0 ? document : elems[0];
    
    if (elem !== document) {
        elem.getElementById = function(id) {
            return document.getElementById(id);
        };
    }
    return elem.shadowRoot ? elem.shadowRoot : elem;
}

function switch_to_img2img() {
    console.log("[Photo Message] Switching to img2img tab...");
    const tabs = gradioApp().querySelector('#tabs');
    if (!tabs) {
        console.error("[Photo Message] Could not find tabs element");
        return;
    }
    
    // Use A1111's built-in switch_to_img2img function if available
    if (typeof window.switch_to_img2img === 'function') {
        console.log("[Photo Message] Using A1111's switch_to_img2img function");
        window.switch_to_img2img();
    } else {
        console.log("[Photo Message] Using fallback tab switching");
        tabs.querySelectorAll('button')[1].click();
    }
    
    // Wait a bit for the tab to switch before setting the image
    setTimeout(() => {
        console.log("[Photo Message] Setting image in img2img...");
        const img2imgImage = gradioApp().querySelector('#img2img_image');
        const previewImage = gradioApp().querySelector('#photo_message_image img');
        
        if (!img2imgImage) {
            console.error("[Photo Message] Could not find img2img_image element");
            return;
        }
        if (!previewImage) {
            console.error("[Photo Message] Could not find preview image");
            return;
        }
        
        try {
            let imgData = previewImage.src;
            console.log("[Photo Message] Got image data:", imgData.substring(0, 100) + "...");
            
            // If it's not already a data URL, convert it
            if (!imgData.startsWith('data:')) {
                console.log("[Photo Message] Converting to data URL");
                imgData = 'data:image/jpeg;base64,' + imgData;
            }
            
            // Create a file input event
            const uploadButton = img2imgImage.querySelector('input[type="file"]');
            if (uploadButton) {
                console.log("[Photo Message] Found upload button, creating file...");
                
                // Create a blob from the base64 data
                const byteString = atob(imgData.split(',')[1]);
                const mimeString = imgData.split(',')[0].split(':')[1].split(';')[0];
                const ab = new ArrayBuffer(byteString.length);
                const ia = new Uint8Array(ab);
                for (let i = 0; i < byteString.length; i++) {
                    ia[i] = byteString.charCodeAt(i);
                }
                const blob = new Blob([ab], {type: mimeString});
                const file = new File([blob], "image.jpg", {type: mimeString});
                
                // Create a DataTransfer and dispatch the event
                const dt = new DataTransfer();
                dt.items.add(file);
                uploadButton.files = dt.files;
                
                // Dispatch both change and input events
                uploadButton.dispatchEvent(new Event('change', { bubbles: true }));
                uploadButton.dispatchEvent(new Event('input', { bubbles: true }));
                
                console.log("[Photo Message] Image set successfully");
            } else {
                console.error("[Photo Message] Could not find upload button");
            }
        } catch (error) {
            console.error("[Photo Message] Error setting image:", error);
        }
    }, 100);
}

function switch_to_extras() {
    console.log("[Photo Message] Switching to extras tab...");
    const tabs = gradioApp().querySelector('#tabs');
    if (!tabs) {
        console.error("[Photo Message] Could not find tabs element");
        return;
    }
    
    // Use A1111's built-in switch_to_extras function if available
    if (typeof window.switch_to_extras === 'function') {
        console.log("[Photo Message] Using A1111's switch_to_extras function");
        window.switch_to_extras();
    } else {
        console.log("[Photo Message] Using fallback tab switching");
        tabs.querySelectorAll('button')[2].click();
    }
    
    // Wait a bit for the tab to switch before setting the image
    setTimeout(() => {
        console.log("[Photo Message] Setting image in extras...");
        const extrasImage = gradioApp().querySelector('#extras_image');
        const previewImage = gradioApp().querySelector('#photo_message_image img');
        
        if (!extrasImage) {
            console.error("[Photo Message] Could not find extras_image element");
            return;
        }
        if (!previewImage) {
            console.error("[Photo Message] Could not find preview image");
            return;
        }
        
        try {
            let imgData = previewImage.src;
            console.log("[Photo Message] Got image data:", imgData.substring(0, 100) + "...");
            
            // If it's not already a data URL, convert it
            if (!imgData.startsWith('data:')) {
                console.log("[Photo Message] Converting to data URL");
                imgData = 'data:image/jpeg;base64,' + imgData;
            }
            
            // Create a file input event
            const uploadButton = extrasImage.querySelector('input[type="file"]');
            if (uploadButton) {
                console.log("[Photo Message] Found upload button, creating file...");
                
                // Create a blob from the base64 data
                const byteString = atob(imgData.split(',')[1]);
                const mimeString = imgData.split(',')[0].split(':')[1].split(';')[0];
                const ab = new ArrayBuffer(byteString.length);
                const ia = new Uint8Array(ab);
                for (let i = 0; i < byteString.length; i++) {
                    ia[i] = byteString.charCodeAt(i);
                }
                const blob = new Blob([ab], {type: mimeString});
                const file = new File([blob], "image.jpg", {type: mimeString});
                
                // Create a DataTransfer and dispatch the event
                const dt = new DataTransfer();
                dt.items.add(file);
                uploadButton.files = dt.files;
                
                // Dispatch both change and input events
                uploadButton.dispatchEvent(new Event('change', { bubbles: true }));
                uploadButton.dispatchEvent(new Event('input', { bubbles: true }));
                
                console.log("[Photo Message] Image set successfully");
            } else {
                console.error("[Photo Message] Could not find upload button");
            }
        } catch (error) {
            console.error("[Photo Message] Error setting image:", error);
        }
    }, 100);
}
"""

# Store received photos
photos = []

class PhotoMessage:
    def __init__(self, image_data, name, message, timestamp, is_sent=False):
        # Remove any existing prefix to ensure clean data
        if isinstance(image_data, str) and 'base64,' in image_data:
            self.image_data = image_data.split('base64,')[1]
        else:
            self.image_data = image_data
        self.name = name
        self.message = message
        self.timestamp = timestamp
        self.is_sent = is_sent

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
                # Handle base64 data without prefix
                image_data = photo.image_data
                if not image_data.startswith('data:image/jpeg;base64,'):
                    image_data = f"data:image/jpeg;base64,{image_data}"
                    
                # Convert base64 to image data
                image_bytes = base64.b64decode(image_data.split('base64,')[1])
                # Create a PIL Image from bytes
                image = Image.open(io.BytesIO(image_bytes))
                return image
            except Exception as e:
                print(f"Error decoding image: {e}")
                print(traceback.format_exc())
                return None
    return None

def update_photo_list():
    photo_data = [[p.timestamp, p.name, p.message, "✓" if p.is_sent else ""] for p in photos]
    print(f"[Photo Message] Updating photo list with {len(photo_data)} photos")
    # Convert to DataFrame with sent status
    df = pd.DataFrame(photo_data, columns=["Time", "Name", "Message", "Sent"])
    return df

def on_select(evt: gr.SelectData, current_value):
    """Handle selection of a photo from the list"""
    try:
        print(f"[Photo Message] Selection event: {evt.index}")
        print(f"[Photo Message] Current dataframe value:\n{current_value}")
        
        if current_value is None or len(current_value.index) == 0:
            print("[Photo Message] No data in DataFrame")
            return None
            
        try:
            row_idx = evt.index[0]  # Get the row index from the selection event
            if row_idx >= len(current_value.index):
                print("[Photo Message] Selected index out of range")
                return None
                
            # Get timestamp from the first column
            timestamp = current_value.iloc[row_idx, 0]
            print(f"[Photo Message] Selected timestamp: {timestamp}")
            
            # Debug info
            print(f"[Photo Message] Current photos in memory: {len(photos)}")
            for p in photos:
                print(f"[Photo Message] Stored photo: {p.timestamp}, {p.name}")
            
            # Get the photo using the timestamp
            image = get_photo_by_timestamp(timestamp)
            if image:
                print("[Photo Message] Successfully loaded selected image")
                return image
            else:
                print("[Photo Message] Could not find image for timestamp")
                return None
                
        except IndexError as ie:
            print(f"[Photo Message] Index error: {ie}")
            return None
            
    except Exception as e:
        print(f"[Photo Message] Error in on_select: {str(e)}")
        print(traceback.format_exc())
        return None

def send_image_to_tab(image):
    """Handle sending an image to another tab"""
    try:
        if image is None:
            print("[Photo Message] No image provided to send")
            return "No image selected"
            
        print("[Photo Message] Image provided for sending")
        return "Image ready to send"
            
    except Exception as e:
        error_msg = f"Error preparing image: {str(e)}"
        print(f"[Photo Message] {error_msg}")
        print(traceback.format_exc())
        return error_msg

def format_base64_image(img_data):
    """Ensure image data has the correct base64 prefix"""
    try:
        if isinstance(img_data, str):
            # If it's already a string (base64)
            # First remove any existing prefix
            if 'base64,' in img_data:
                img_data = img_data.split('base64,')[1]
            return f"data:image/jpeg;base64,{img_data}"
        else:
            # If it's a PIL Image
            buffered = io.BytesIO()
            if img_data.mode != 'RGB':
                img_data = img_data.convert('RGB')
            img_data.save(buffered, format="JPEG", quality=95)
            img_str = base64.b64encode(buffered.getvalue()).decode()
            return f"data:image/jpeg;base64,{img_str}"
    except Exception as e:
        print(f"Error formatting base64 image: {e}")
        print(traceback.format_exc())
        return None

def send_to_api(source_photo_data, generated_image, current_url):
    if source_photo_data is None or generated_image is None:
        return "Please select both a source photo and a generated image"
        
    try:
        print("[Photo Message] Sending images to API...")
        print(f"[Photo Message] Using display app URL: {current_url}")
        
        # Get metadata from source photo
        source_photo = None
        for photo in photos:
            if photo.timestamp == source_photo_data['timestamp']:
                source_photo = photo
                if photo.is_sent:
                    return "This photo has already been processed"
                break
                
        if source_photo is None:
            return "Source photo not found in memory"
            
        # Format both images consistently
        source_img = format_base64_image(source_photo.image_data)
        generated_img = format_base64_image(generated_image)
        
        if not source_img or not generated_img:
            return "Error formatting images"
            
        payload = {
            "source_image": source_img,
            "generated_image": generated_img,
            "name": source_photo.name,
            "message": source_photo.message,
            "timestamp": source_photo.timestamp
        }
        
        print("[Photo Message] Payload preview:")
        print(f"- Name: {payload['name']}")
        print(f"- Message: {payload['message']}")
        print(f"- Timestamp: {payload['timestamp']}")
        print(f"- Source image prefix: {source_img[:50]}")
        print(f"- Generated image prefix: {generated_img[:50]}")
        
        try:
            # First try WebSocket if available
            if hasattr(sio, 'connected') and sio.connected:
                print("[Photo Message] Sending via WebSocket...")
                sio.emit('new_photo', payload)
                
                # Mark the photo as sent
                source_photo.is_sent = True
                update_photo_list()  # Update UI immediately
                
                print("[Photo Message] Successfully sent via WebSocket")
                return "Images sent successfully via WebSocket"
                
            # Fallback to HTTP endpoint
            print("[Photo Message] WebSocket not available, sending via HTTP...")
            response = requests.post(
                f"{current_url}/new_photo",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                # Mark the photo as sent
                source_photo.is_sent = True
                update_photo_list()  # Update UI immediately
                
                print("[Photo Message] Successfully sent via HTTP")
                return "Images sent successfully via HTTP"
            else:
                error_msg = f"Error sending images: {response.status_code} - {response.text}"
                print(f"[Photo Message] {error_msg}")
                return error_msg
                
        except requests.exceptions.ConnectionError:
            error_msg = "Could not connect to display app - make sure it's running"
            print(f"[Photo Message] {error_msg}")
            return error_msg
        except Exception as e:
            error_msg = f"Error sending to display app: {str(e)}"
            print(f"[Photo Message] {error_msg}")
            print(traceback.format_exc())
            return error_msg
            
    except Exception as e:
        error_msg = f"Error preparing images: {str(e)}"
        print(f"[Photo Message] {error_msg}")
        print(traceback.format_exc())
        return error_msg

def on_ui_tabs():
    """Register UI components"""
    try:
        print("\n[Photo Message] Creating UI tab...")
        
        # Import required modules
        from modules import shared, scripts, script_callbacks, ui, images
        import modules.scripts as scripts_module
        
        with gr.Blocks(analytics_enabled=False) as photo_message_tab:
            # Store display app URL in state
            display_app_url = gr.State(value="http://localhost:5001")
            
            with gr.Row(equal_height=True):
                gr.Markdown("## 📸 Photo Message Extension")
            
            # Settings row
            with gr.Row(variant="panel"):
                with gr.Column(scale=1):
                    display_app_input = gr.Textbox(
                        label="Display App URL",
                        placeholder="Enter display app URL (e.g., localhost:5001)",
                        value="localhost:5001",
                        show_label=True,
                        elem_id="display_app_url"
                    )
                    connect_btn = gr.Button("🔌 Connect", size="sm", variant="primary")
                with gr.Column(scale=2):
                    connection_status = gr.Textbox(
                        label="Connection Status",
                        value="Not connected",
                        interactive=False
                    )
            
            # Main content area
            with gr.Row(variant="panel"):
                # Left panel - Received Photos
                with gr.Column(scale=2, variant="panel"):
                    gr.Markdown("### 📥 Received Photos")
                    with gr.Row():
                        # Initialize with DataFrame including sent status
                        initial_df = pd.DataFrame(
                            [[p.timestamp, p.name, p.message, "✓" if p.is_sent else ""] for p in photos],
                            columns=["Time", "Name", "Message", "Sent"]
                        )
                        photo_list = gr.Dataframe(
                            headers=["Time", "Name", "Message", "Sent"],
                            row_count=8,
                            col_count=(4, "fixed"),
                            interactive=True,
                            elem_id="photo_list",
                            value=initial_df
                        )
                    with gr.Row():
                        refresh_btn = gr.Button("🔄 Refresh List", size="sm", variant="secondary")
                    
                    # Preview area for selected photo
                    with gr.Column():
                        preview_image = gr.Image(
                            label="Selected Source Photo",
                            show_label=True,
                            interactive=False,
                            type="pil",
                            elem_id="photo_message_image",
                            height=300
                        )
                        with gr.Row():
                            send_to_img2img = gr.Button('📝 Send to Img2img', elem_id="photo_message_send_to_img2img", variant="primary")
                            send_to_extras = gr.Button('🔧 Send to Extras', elem_id="photo_message_send_to_extras", variant="primary")
                        status_text = gr.Textbox(label="Status", interactive=False, value="No image selected", visible=True)
                        selected_photo_info = gr.JSON(
                            label="Selected Photo Info",
                            visible=False
                        )
                
                # Right panel - Generated Images
                with gr.Column(scale=3, variant="panel"):
                    with gr.Row():
                        gr.Markdown("### 🎨 Generated Images")
                        refresh_generated_btn = gr.Button("🔄 Refresh", size="sm", variant="secondary")
                    
                    generated_gallery = gr.Gallery(
                        label="Recent Generations",
                        show_label=False,
                        elem_id="photo_message_generated",
                        columns=4,
                        height=300,
                        preview=True
                    )
                    
                    with gr.Column():
                        selected_generated_image = gr.Image(
                            label="Selected Generated Image",
                            show_label=True,
                            interactive=False,
                            type="pil",
                            elem_id="selected_generated_image",
                            height=200
                        )
                        with gr.Row():
                            send_selected_btn = gr.Button(
                                "📤 Send to Display App",
                                size="sm",
                                variant="primary",
                                interactive=False  # Initially disabled
                            )
                        send_status = gr.Textbox(
                            label="Send Status",
                            interactive=False,
                            visible=True
                        )
            
            # Help text at the bottom
            with gr.Row(variant="panel"):
                gr.Markdown("""
                ### 📋 Instructions
                - **Received Photos**: View and manage photos received from other applications
                - **Generated Images**: Browse and share your recent AI-generated images
                - Click on any image to select it for preview and sharing
                """)
            
            def get_generated_images():
                """Get all generated images from output directories"""
                try:
                    print("[Photo Message] Getting generated images...")
                    image_paths = []
                    
                    # Get paths from various output directories
                    dirs_to_check = []
                    
                    # Get output directories from shared options
                    if hasattr(shared.opts, 'outdir_samples'):
                        dirs_to_check.append(shared.opts.outdir_samples)
                    if hasattr(shared.opts, 'outdir_txt2img_samples'):
                        dirs_to_check.append(shared.opts.outdir_txt2img_samples)
                    if hasattr(shared.opts, 'outdir_img2img_samples'):
                        dirs_to_check.append(shared.opts.outdir_img2img_samples)
                    if hasattr(shared.opts, 'outdir_extras_samples'):
                        dirs_to_check.append(shared.opts.outdir_extras_samples)
                    
                    print(f"[Photo Message] Checking directories: {dirs_to_check}")
                    
                    # Keep track of processed files to avoid duplicates
                    processed_files = set()
                    
                    for dir_path in dirs_to_check:
                        if dir_path and os.path.exists(dir_path):
                            print(f"[Photo Message] Scanning directory: {dir_path}")
                            
                            # Get all image files in directory and subdirectories
                            for root, _, files in os.walk(dir_path):
                                for filename in files:
                                    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                                        full_path = os.path.join(root, filename)
                                        
                                        # Skip if we've already processed this file
                                        if full_path in processed_files:
                                            continue
                                            
                                        try:
                                            # Get file modification time
                                            mtime = os.path.getmtime(full_path)
                                            
                                            # Only include files from the last hour
                                            if time.time() - mtime <= 3600:  # 3600 seconds = 1 hour
                                                image_paths.append((full_path, mtime))
                                                processed_files.add(full_path)
                                        except Exception as e:
                                            print(f"[Photo Message] Error getting file info for {full_path}: {e}")
                    
                    if not image_paths:
                        print("[Photo Message] No recent generated images found")
                        return []
                        
                    # Sort by modification time (newest first)
                    image_paths.sort(key=lambda x: x[1], reverse=True)
                    
                    # Load images
                    loaded_images = []
                    for path, _ in image_paths[:20]:  # Limit to 20 most recent images
                        try:
                            # Try to read generation parameters from the image
                            img = Image.open(path)
                            
                            # Try to get generation info
                            try:
                                geninfo = ''
                                if hasattr(images, 'read_info_from_image'):
                                    geninfo, _ = images.read_info_from_image(img)
                                print(f"[Photo Message] Image info for {path}: {geninfo[:100]}...")
                            except Exception as e:
                                print(f"[Photo Message] Could not read image info: {e}")
                            
                            loaded_images.append(img)
                            print(f"[Photo Message] Loaded image: {path}")
                        except Exception as e:
                            print(f"[Photo Message] Error loading image {path}: {e}")
                            continue
                    
                    print(f"[Photo Message] Successfully loaded {len(loaded_images)} images")
                    return loaded_images
                    
                except Exception as e:
                    print(f"[Photo Message] Error getting generated images: {e}")
                    print(traceback.format_exc())
                    return []
            
            def update_send_button_state(source_info, generated_img):
                """Update the send button state based on selection state"""
                try:
                    print("[Photo Message] Updating send button state...")
                    print(f"Source info: {source_info}")
                    print(f"Generated image type: {type(generated_img)}")
                    
                    # Check if we have both a source photo and a generated image
                    has_source = source_info is not None and isinstance(source_info, dict)
                    has_generated = generated_img is not None
                    
                    if has_source and has_generated:
                        if source_info.get('is_sent', False):
                            print("[Photo Message] Source photo already sent")
                            return gr.Button.update(interactive=False, value="Already Sent")
                        else:
                            print("[Photo Message] Both images selected, enabling button")
                            return gr.Button.update(interactive=True, value="📤 Send to Display App")
                    else:
                        print("[Photo Message] Missing required selections")
                        return gr.Button.update(interactive=False, value="Select both images")
                    
                except Exception as e:
                    print(f"[Photo Message] Error updating button state: {e}")
                    print(traceback.format_exc())
                    return gr.Button.update(interactive=False, value="Error")
            
            def on_photo_select(evt: gr.SelectData, current_value):
                try:
                    if current_value is None or len(current_value.index) == 0:
                        return None, None
                        
                    row_idx = evt.index[0]
                    if row_idx >= len(current_value.index):
                        return None, None
                        
                    timestamp = current_value.iloc[row_idx, 0]
                    
                    # Find the photo in our list
                    for photo in photos:
                        if photo.timestamp == timestamp:
                            # Create info dict with metadata and sent status
                            photo_info = {
                                'timestamp': photo.timestamp,
                                'name': photo.name,
                                'message': photo.message,
                                'is_sent': photo.is_sent
                            }
                            
                            # Get the image
                            try:
                                image_bytes = base64.b64decode(photo.image_data)
                                image = Image.open(io.BytesIO(image_bytes))
                                return image, photo_info
                            except Exception as e:
                                print(f"Error decoding image: {e}")
                                return None, None
                                
                    return None, None
                except Exception as e:
                    print(f"Error in photo selection: {e}")
                    print(traceback.format_exc())
                    return None, None
            
            # Wire up the events
            refresh_btn.click(fn=update_photo_list, outputs=[photo_list])
            
            # Update source photo selection
            photo_list.select(
                fn=on_photo_select,
                inputs=[photo_list],
                outputs=[preview_image, selected_photo_info]
            ).then(
                fn=update_send_button_state,
                inputs=[selected_photo_info, selected_generated_image],
                outputs=[send_selected_btn]
            )
            
            # Update generated image selection
            generated_gallery.select(
                fn=on_gallery_select,
                inputs=[generated_gallery],
                outputs=[selected_generated_image]
            ).then(
                fn=update_send_button_state,
                inputs=[selected_photo_info, selected_generated_image],
                outputs=[send_selected_btn]
            )
            
            # Connect send button to API
            send_selected_btn.click(
                fn=send_to_api,
                inputs=[selected_photo_info, selected_generated_image, display_app_url],
                outputs=[send_status]
            ).then(
                fn=update_photo_list,
                outputs=[photo_list]
            ).then(
                fn=update_send_button_state,
                inputs=[selected_photo_info, selected_generated_image],
                outputs=[send_selected_btn]
            )
            
            # Add click handlers for the buttons with image data
            send_to_img2img.click(
                fn=send_image_to_tab,
                inputs=[preview_image],
                outputs=[status_text],
                _js="""
                async (img_data) => {
                    if (!img_data) return "No image selected";
                    console.log("[Photo Message] Sending to img2img...");
                    
                    // Switch to img2img tab
                    const tabs = gradioApp().querySelector('#tabs');
                    if (tabs) tabs.querySelectorAll('button')[1].click();
                    
                    await new Promise(r => setTimeout(r, 100));  // Wait for tab switch
                    
                    try {
                        // Find and activate reActor
                        const scriptDropdown = gradioApp().querySelector('#script_list');
                        if (scriptDropdown) {
                            // Find the reActor option
                            const options = Array.from(scriptDropdown.options);
                            const reactorOption = options.find(opt => opt.textContent.toLowerCase().includes('reactor'));
                            if (reactorOption) {
                                scriptDropdown.value = reactorOption.value;
                                scriptDropdown.dispatchEvent(new Event('change'));
                                console.log("[Photo Message] Activated reActor");
                            }
                        }

                        // Set the image in img2img
                        const img2imgInput = gradioApp().querySelector('#img2img_image input[type="file"]');
                        if (!img2imgInput) {
                            console.error("[Photo Message] Could not find img2img input");
                            return "Could not find img2img input";
                        }
                        
                        // Create file from image data
                        const res = await fetch(img_data);
                        const blob = await res.blob();
                        const file = new File([blob], "image.png", { type: "image/png" });
                        
                        // Set the file
                        const dt = new DataTransfer();
                        dt.items.add(file);
                        img2imgInput.files = dt.files;
                        img2imgInput.dispatchEvent(new Event('change', { bubbles: true }));

                        // Wait for image to load
                        await new Promise(r => setTimeout(r, 200));

                        // Set reActor settings
                        const reactorSettings = gradioApp().querySelector('#script_reactor_div');
                        if (reactorSettings) {
                            // Find and click the restore face checkbox
                            const restoreFaceCheckbox = reactorSettings.querySelector('input[type="checkbox"]');
                            if (restoreFaceCheckbox && !restoreFaceCheckbox.checked) {
                                restoreFaceCheckbox.click();
                            }

                            // Set upscaler to 4x-UltraSharp
                            const upscalerDropdown = reactorSettings.querySelector('select');
                            if (upscalerDropdown) {
                                const ultraSharpOption = Array.from(upscalerDropdown.options)
                                    .find(opt => opt.textContent.includes('4x-UltraSharp'));
                                if (ultraSharpOption) {
                                    upscalerDropdown.value = ultraSharpOption.value;
                                    upscalerDropdown.dispatchEvent(new Event('change'));
                                }
                            }
                        }
                        
                        console.log("[Photo Message] Image sent successfully");
                        return "Image sent to img2img with reActor activated";
                    } catch (error) {
                        console.error("[Photo Message] Error:", error);
                        return "Error sending image: " + error.message;
                    }
                }
                """
            )
            
            send_to_extras.click(
                fn=send_image_to_tab,
                inputs=[preview_image],
                outputs=[status_text],
                _js="""
                async (img_data) => {
                    if (!img_data) return "No image selected";
                    console.log("[Photo Message] Sending to extras...");
                    
                    // Switch to extras tab
                    const tabs = gradioApp().querySelector('#tabs');
                    if (tabs) tabs.querySelectorAll('button')[2].click();
                    
                    await new Promise(r => setTimeout(r, 100));  // Wait for tab switch
                    
                    try {
                        const extrasInput = gradioApp().querySelector('#extras_image input[type="file"]');
                        if (!extrasInput) {
                            console.error("[Photo Message] Could not find extras input");
                            return "Could not find extras input";
                        }
                        
                        // Create file from image data
                        const res = await fetch(img_data);
                        const blob = await res.blob();
                        const file = new File([blob], "image.png", { type: "image/png" });
                        
                        // Set the file
                        const dt = new DataTransfer();
                        dt.items.add(file);
                        extrasInput.files = dt.files;
                        extrasInput.dispatchEvent(new Event('change', { bubbles: true }));
                        
                        console.log("[Photo Message] Image sent successfully");
                        return "Image sent to extras";
                    } catch (error) {
                        console.error("[Photo Message] Error:", error);
                        return "Error sending image: " + error.message;
                    }
                }
                """
            )
            
            # Connect refresh button to get_generated_images
            refresh_generated_btn.click(
                fn=get_generated_images,
                outputs=[generated_gallery]
            )
            
            def update_display_app_url(url):
                """Update the display app URL and attempt to reconnect"""
                try:
                    # Format the URL properly
                    if not url.startswith('http://'):
                        url = f"http://{url}"
                    
                    print(f"[Photo Message] Updating display app URL to: {url}")
                    
                    # Try to connect to new URL
                    try:
                        if hasattr(sio, 'connected') and sio.connected:
                            sio.disconnect()
                        
                        time.sleep(1)  # Wait before reconnecting
                        sio.connect(url, wait_timeout=5, wait=True)
                        print("[Photo Message] Successfully connected to new URL")
                        return url, "Connected successfully"
                    except Exception as e:
                        error_msg = f"Could not connect to {url}: {str(e)}"
                        print(f"[Photo Message] {error_msg}")
                        return url, error_msg
                        
                except Exception as e:
                    error_msg = f"Error updating URL: {str(e)}"
                    print(f"[Photo Message] {error_msg}")
                    return url, error_msg
            
            # Connect button handler
            connect_btn.click(
                fn=update_display_app_url,
                inputs=[display_app_input],
                outputs=[display_app_url, connection_status]
            )
            
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

def on_gallery_select(evt: gr.SelectData, gallery):
    """Handle selection of an image from the generated images gallery"""
    try:
        print(f"[Photo Message] Gallery selection event: {evt.index}")
        if gallery is None or not isinstance(gallery, list):
            print("[Photo Message] Gallery is empty or invalid")
            return None
        
        if evt.index >= len(gallery):
            print("[Photo Message] Selected index out of range")
            return None
            
        selected = gallery[evt.index]
        print(f"[Photo Message] Selected image type: {type(selected)}")
        print(f"[Photo Message] Selected image data: {selected}")  # Debug print
        
        # Handle dictionary case from gallery
        if isinstance(selected, dict):
            # Try to get the file path from the dictionary
            if 'name' in selected:
                # Use the local file path directly
                file_path = selected['name']
                print(f"[Photo Message] Using file path: {file_path}")
                try:
                    img = Image.open(file_path)
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    print("[Photo Message] Successfully loaded image from temp file")
                    return img
                except Exception as e:
                    print(f"[Photo Message] Error opening temp file: {e}")
                    
            # If we couldn't get the file directly, try the data URL
            if 'data' in selected and isinstance(selected['data'], str):
                if selected['data'].startswith('http'):
                    try:
                        response = requests.get(selected['data'], timeout=5)
                        if response.status_code == 200:
                            img = Image.open(io.BytesIO(response.content))
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                            print("[Photo Message] Successfully loaded image from URL")
                            return img
                    except Exception as e:
                        print(f"[Photo Message] Error loading from URL: {e}")
                        
            print(f"[Photo Message] Available keys in dict: {list(selected.keys())}")
            return None
        
        # If it's already a PIL Image, return it
        if isinstance(selected, Image.Image):
            if selected.mode != 'RGB':
                selected = selected.convert('RGB')
            print("[Photo Message] Successfully selected PIL Image from gallery")
            return selected
            
        # Handle path string
        if isinstance(selected, str):
            try:
                img = Image.open(selected)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                print("[Photo Message] Successfully loaded image from path")
                return img
            except Exception as e:
                print(f"[Photo Message] Error opening image from path: {e}")
                return None
                
        # Handle numpy array
        if isinstance(selected, np.ndarray):
            try:
                img = Image.fromarray(selected)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                print("[Photo Message] Successfully converted numpy array to image")
                return img
            except Exception as e:
                print(f"[Photo Message] Error converting numpy array: {e}")
                return None
                
        print(f"[Photo Message] Unsupported image type: {type(selected)}")
        return None
        
    except Exception as e:
        print(f"[Photo Message] Error in gallery selection: {e}")
        print(traceback.format_exc())
        return None

# Improve WebSocket connection handling
def connect_to_display_app():
    """Attempt to connect to the display app with better error handling"""
    try:
        if hasattr(sio, 'connected') and sio.connected:
            print("[Photo Message] Already connected to display app")
            return True
            
        print("[Photo Message] Attempting to connect to display app...")
        
        # Ensure we're disconnected first
        try:
            sio.disconnect()
        except:
            pass
            
        # Wait a moment before reconnecting
        time.sleep(1)
        
        # Connect with a timeout
        sio.connect('http://localhost:5001', wait_timeout=5, wait=True)
        print("[Photo Message] Successfully connected to display app")
        return True
        
    except Exception as e:
        print(f"[Photo Message] Could not connect to display app: {e}")
        print("[Photo Message] Will retry connection when sending images")
        return False

# Update the initial connection attempt
try:
    connect_to_display_app()
except Exception as e:
    print(f"[Photo Message] Initial connection attempt failed: {e}") 