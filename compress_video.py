from moviepy import VideoFileClip
import os

input_path = "images/Omnidictate.mp4"
output_path = "images/Omnidictate_compressed.mp4"
target_size_mb = 8.5

def compress_video(input_path, output_path, target_size_mb):
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found")
        return

    clip = VideoFileClip(input_path)
    duration = clip.duration
    print(f"Duration: {duration} seconds")
    print(f"Original Size: {clip.size}")
    
    # Calculate target bitrate
    # Size (bits) = Bitrate (bps) * Duration (s)
    # Bitrate = Size / Duration
    target_size_bits = target_size_mb * 8 * 1024 * 1024
    target_bitrate = int(target_size_bits / duration)
    
    print(f"Target Bitrate: {target_bitrate} bps")

    # If bitrate is very low, resize
    resize_factor = 1.0
    if target_bitrate < 500000: # Less than 500kbps
        resize_factor = 0.5
        print("Bitrate low, resizing by 0.5")
    elif target_bitrate < 1000000: # Less than 1Mbps
        resize_factor = 0.75
        print("Bitrate moderate, resizing by 0.75")
        
    if resize_factor != 1.0:
        clip = clip.resized(resize_factor)
        print(f"New Size: {clip.size}")

    # Write video
    # Note: moviepy uses 'bitrate' string like '500k'
    bitrate_str = f"{int(target_bitrate/1000)}k"
    print(f"Encoding with bitrate: {bitrate_str}")
    
    clip.write_videofile(output_path, bitrate=bitrate_str, preset='medium', codec='libx264', audio_codec='aac')
    
    clip.close()
    
    final_size = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Compression complete. Final size: {final_size:.2f} MB")

if __name__ == "__main__":
    compress_video(input_path, output_path, target_size_mb)
