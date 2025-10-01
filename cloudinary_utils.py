import cloudinary
import cloudinary.uploader

cloudinary.config(
  cloud_name='SEU_CLOUD_NAME',
  api_key='SUA_API_KEY',
  api_secret='SEU_API_SECRET',
  secure=True
)

def upload_image_to_cloudinary(file_stream, filename):
    result = cloudinary.uploader.upload(file_stream, public_id=filename, folder="espelho_pessoal")
    return result['secure_url']
