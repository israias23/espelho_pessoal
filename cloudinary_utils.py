import cloudinary
import cloudinary.uploader

cloudinary.config(
  cloud_name='dznn4uaff',
  api_key='641122556492738',
  api_secret='oMznUr6qnNMVzpMuGPdcB9iS7AA',
  secure=True
)

def upload_image_to_cloudinary(file_stream, filename):
    result = cloudinary.uploader.upload(file_stream, public_id=filename, folder="espelho_pessoal")
    return result['secure_url']
