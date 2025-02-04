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

print("\n[Photo Message] ====== Extension Loading ======")
print(f"[Photo Message] Current directory: {os.path.dirname(os.path.abspath(__file__))}")
print(f"[Photo Message] Python path: {sys.path}")

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
        
        # Import required modules
        from modules import shared, scripts, script_callbacks, ui, images
        import modules.scripts as scripts_module
        
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
                        elem_id="photo_message_image",
                        height=400
                    )
                    with gr.Row(elem_id="photo_message_buttons", elem_classes="image-buttons"):
                        send_to_img2img = gr.Button('🖼️', elem_id="photo_message_send_to_img2img", tooltip="Send image to img2img tab", variant="tool")
                        send_to_extras = gr.Button('📐', elem_id="photo_message_send_to_extras", tooltip="Send image to extras tab", variant="tool")
                    status_text = gr.Textbox(label="Status", interactive=False, value="No image selected")
            
            # Add gallery for generated images
            with gr.Row():
                with gr.Column():
                    gr.Markdown("## Generated Images")
                    generated_gallery = gr.Gallery(
                        label="Generated Images",
                        show_label=True,
                        elem_id="photo_message_generated",
                        columns=4,
                        height=400,
                        preview=True
                    )
                    selected_generated_image = gr.Image(
                        label="Selected Generated Image",
                        show_label=True,
                        interactive=False,
                        visible=False,
                        type="pil"
                    )
                    with gr.Row():
                        refresh_generated_btn = gr.Button("🔄 Refresh Generated", size="sm")
                        send_selected_btn = gr.Button("📤 Send Selected Image", size="sm")
                        clear_generated_btn = gr.Button("🗑️ Clear", size="sm")
            
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
            
            def send_to_api(image):
                if image is not None:
                    try:
                        print("[Photo Message] Sending image to API...")
                        # Convert PIL Image to base64
                        buffered = io.BytesIO()
                        image.save(buffered, format="JPEG", quality=95)
                        img_str = base64.b64encode(buffered.getvalue()).decode()
                        
                        # Add data:image/jpeg;base64 prefix as expected by display app
                        img_data = f"data:image/jpeg;base64,{img_str}"
                        
                        # Prepare the payload matching display app expectations
                        payload = {
                            "image_data": img_data,
                            "name": "Stable Diffusion",
                            "message": "Generated with A1111",
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        try:
                            # First try WebSocket if available
                            if hasattr(sio, 'connected') and sio.connected:
                                print("[Photo Message] Sending via WebSocket...")
                                sio.emit('new_photo', json.dumps(payload))
                                return "Image sent successfully via WebSocket"
                                
                            # Fallback to HTTP endpoint
                            print("[Photo Message] Sending via HTTP...")
                            response = requests.post(
                                "http://localhost:5001/new_photo",
                                json=payload,
                                headers={"Content-Type": "application/json"},
                                timeout=10
                            )
                            
                            if response.status_code == 200:
                                return "Image sent successfully via HTTP"
                            else:
                                error_msg = f"Error sending image: {response.status_code} - {response.text}"
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
                        error_msg = f"Error preparing image: {str(e)}"
                        print(f"[Photo Message] {error_msg}")
                        print(traceback.format_exc())
                        return error_msg
                        
                return "No image selected"
            
            def on_gallery_select(evt: gr.SelectData, images):
                if images is not None and evt.index < len(images):
                    return images[evt.index]
                return None
            
            # Wire up the events
            refresh_btn.click(fn=update_photo_list, outputs=[photo_list])
            photo_list.select(fn=on_select, inputs=[photo_list], outputs=[preview_image])
            
            # Gallery events
            refresh_generated_btn.click(
                fn=get_generated_images,
                outputs=[generated_gallery]
            )
            
            generated_gallery.select(
                fn=on_gallery_select,
                inputs=[generated_gallery],
                outputs=[selected_generated_image]
            )
            
            clear_generated_btn.click(
                fn=lambda: None,
                outputs=[generated_gallery]
            )
            
            send_selected_btn.click(
                fn=send_to_api,
                inputs=[selected_generated_image],
                outputs=[status_text]
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
                        
                        console.log("[Photo Message] Image sent successfully");
                        return "Image sent to img2img";
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