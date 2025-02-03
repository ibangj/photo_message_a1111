from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from scripts.main import PhotoMessage, photos, display_app_url  # Changed from relative to absolute import

class PhotoData(BaseModel):
    image: str
    name: str
    message: str
    display_app_url: str = None  # Optional display app URL

def on_app_started(demo: FastAPI):
    @demo.post("/sdapi/v1/photo_message/receive")
    async def receive_photo(data: PhotoData):
        try:
            # Update display app URL if provided
            global display_app_url
            if data.display_app_url:
                display_app_url = data.display_app_url
                print(f"Updated display app URL to: {display_app_url}")
            
            # Create new photo message
            photo = PhotoMessage(
                image_data=data.image,
                name=data.name,
                message=data.message,
                timestamp=datetime.now().isoformat()
            )
            
            # Add to queue
            photos.append(photo)
            print(f"Added new photo from {data.name} to queue")
            
            return {"status": "success", "message": "Photo received"}
        except Exception as e:
            print(f"Error in receive_photo: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e)) 