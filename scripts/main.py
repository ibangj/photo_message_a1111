import gradio as gr
import asyncio
import aiohttp
import json
import base64
import traceback
from PIL import Image
import io
from datetime import datetime
from modules import script_callbacks, shared
from modules.processing import process_images, StableDiffusionProcessingImg2Img, StableDiffusionProcessingTxt2Img
from fastapi import FastAPI, Body, HTTPException
from modules.api.models import *

print("Loading Photo Message Extension...")

# Store received photos and their status
photos = []
display_app_url = "http://203.153.109.225:5001"  # Updated to match your config
capture_app_url = "http://203.153.109.225:5000"  # Updated to match your config

class PhotoMessage:
    def __init__(self, image_data, name, message, timestamp, processed=False, sent_to_display=False):
        self.image_data = image_data
        self.name = name
        self.message = message
        self.timestamp = timestamp
        self.processed = processed
        self.sent_to_display = sent_to_display
        self.processed_image = None

async def send_to_display_app(photo):
    """Send processed photo to display app"""
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                'name': photo.name,
                'message': photo.message,
                'image': photo.processed_image,
                'timestamp': photo.timestamp
            }
            async with session.post(f"{display_app_url}/socket.io/", json=payload) as response:
                if response.status == 200:
                    photo.sent_to_display = True
                    return True
    except Exception as e:
        print(f"Error sending to display app: {e}")
    return False

def process_with_img2img(photo, prompt=None):
    """Process photo with img2img"""
    try:
        # Decode base64 image
        image_bytes = base64.b64decode(photo.image_data)
        
        # Create processing object
        p = StableDiffusionProcessingImg2Img(
            init_images=[image_bytes],
            prompt=prompt or "best quality, high resolution photograph, highly detailed",
            negative_prompt="blur, blurry, low quality, text, watermark",
            steps=20,
            denoising_strength=0.4,
            cfg_scale=7,
            sampler_name="DPM++ 2M Karras",
            restore_faces=True
        )
        
        # Process image
        processed = process_images(p)
        if processed and len(processed.images) > 0:
            # Convert processed image to base64
            buffered = processed.images[0]
            photo.processed_image = base64.b64encode(buffered).decode()
            photo.processed = True
            return True
    except Exception as e:
        print(f"Error processing with img2img: {e}")
    return False

def process_with_txt2img(photo, prompt):
    """Process photo with txt2img"""
    try:
        p = StableDiffusionProcessingTxt2Img(
            prompt=prompt,
            negative_prompt="blur, blurry, low quality, text, watermark",
            steps=20,
            cfg_scale=7,
            sampler_name="DPM++ 2M Karras",
            restore_faces=True
        )
        
        processed = process_images(p)
        if processed and len(processed.images) > 0:
            buffered = processed.images[0]
            photo.processed_image = base64.b64encode(buffered).decode()
            photo.processed = True
            return True
    except Exception as e:
        print(f"Error processing with txt2img: {e}")
    return False

def on_ui_tabs():
    try:
        print("Registering Photo Message UI tab...")
        with gr.Blocks(analytics_enabled=False) as photo_message_tab:
            with gr.Row():
                with gr.Column(scale=1):
                    gr.HTML("<h3>📡 Configuration</h3>")
                    display_url_input = gr.Textbox(
                        label="Display App URL",
                        value=display_app_url,
                        placeholder=display_app_url
                    )
                    capture_url_input = gr.Textbox(
                        label="Capture App URL",
                        value=capture_app_url,
                        placeholder=capture_app_url
                    )
                    save_config_btn = gr.Button("💾 Save Configuration")
                    config_status = gr.Textbox(label="Config Status", interactive=False)

            with gr.Row():
                with gr.Column():
                    gr.HTML("<h2>📸 Received Photos</h2>")
                    photo_list = gr.Dataframe(
                        headers=["Time", "Name", "Message", "Status"],
                        row_count=10,
                        col_count=(4, "fixed"),
                        interactive=False
                    )
                    refresh_btn = gr.Button("🔄 Refresh List")
                
                with gr.Column():
                    gr.HTML("<h2>Process Selected Photo</h2>")
                    selected_photo = gr.State(None)
                    preview_img = gr.Image(type="pil", label="Preview")
                    prompt_input = gr.Textbox(label="Custom Prompt (optional)")
                    with gr.Row():
                        img2img_btn = gr.Button("Process with Img2Img")
                        txt2img_btn = gr.Button("Process with Txt2Img")
                    status_text = gr.Textbox(label="Status", interactive=False)

            def update_photo_list():
                return [[p.timestamp, p.name, p.message, 
                        "✅ Processed & Sent" if p.sent_to_display else 
                        "🔄 Processed" if p.processed else 
                        "⏳ Waiting"] for p in photos]

            def select_photo(evt: gr.SelectData):
                selected = photos[evt.index[0]]
                return {
                    selected_photo: selected,
                    preview_img: base64.b64decode(selected.image_data),
                    status_text: "Photo selected for processing"
                }

            def save_configuration(display_url, capture_url):
                global display_app_url, capture_app_url
                display_app_url = display_url.strip()
                capture_app_url = capture_url.strip()
                return f"Configuration saved!\nDisplay App: {display_app_url}\nCapture App: {capture_app_url}"

            async def process_img2img(photo, prompt):
                if photo is None:
                    return "No photo selected"
                
                if process_with_img2img(photo, prompt):
                    if await send_to_display_app(photo):
                        return "Successfully processed and sent to display"
                    return "Processed but failed to send to display"
                return "Failed to process image"

            async def process_txt2img(photo, prompt):
                if photo is None:
                    return "No photo selected"
                if not prompt:
                    return "Prompt is required for txt2img"
                
                if process_with_txt2img(photo, prompt):
                    if await send_to_display_app(photo):
                        return "Successfully processed and sent to display"
                    return "Processed but failed to send to display"
                return "Failed to process image"

            # Event handlers
            save_config_btn.click(
                save_configuration,
                inputs=[display_url_input, capture_url_input],
                outputs=[config_status]
            )
            refresh_btn.click(update_photo_list, outputs=[photo_list])
            photo_list.select(select_photo, outputs=[selected_photo, preview_img, status_text])
            img2img_btn.click(process_img2img, inputs=[selected_photo, prompt_input], outputs=[status_text])
            txt2img_btn.click(process_txt2img, inputs=[selected_photo, prompt_input], outputs=[status_text])

            # Start with empty list
            photo_list.value = update_photo_list()

        print("Photo Message tab created successfully")
        return [(photo_message_tab, "Photo Message", "photo_message_a1111")]
    except Exception as e:
        print(f"Error creating Photo Message tab: {str(e)}")
        print(traceback.format_exc())
        return []

# Register the UI tab
print("Registering callbacks...")
script_callbacks.on_ui_tabs(on_ui_tabs)
print("Callbacks registered")

def on_app_started(demo: FastAPI):
    print("Registering Photo Message API endpoints...")
    try:
        @demo.post("/sdapi/v1/photo_message/receive")
        async def receive_photo(
            image: str = Body(...),
            name: str = Body(...),
            message: str = Body(...),
            display_app_url: str = Body(None)
        ):
            try:
                print(f"Received photo from {name} with message: {message}")
                print(f"API endpoint accessed at: {demo.url_path_for('receive_photo')}")
                
                # Create new photo message
                photo = PhotoMessage(
                    image_data=image,
                    name=name,
                    message=message,
                    timestamp=datetime.now().isoformat()
                )
                
                # Add to queue
                photos.append(photo)
                print(f"Added new photo to queue. Total photos: {len(photos)}")
                
                # Update display app URL if provided
                if display_app_url:
                    global display_app_url
                    display_app_url = display_app_url
                    print(f"Updated display app URL to: {display_app_url}")
                
                return {"status": "success", "message": "Photo received successfully"}
            except Exception as e:
                print(f"Error in receive_photo: {str(e)}")
                print(traceback.format_exc())
                raise HTTPException(status_code=500, detail=str(e))
                
        print("API endpoints registered successfully")
    except Exception as e:
        print(f"Error registering API endpoints: {str(e)}")
        print(traceback.format_exc())

# Register the API endpoints
script_callbacks.on_app_started(on_app_started)
print("Photo Message Extension loaded successfully") 