import os
import shutil
import json
import logging
import time
from pathlib import Path
from typing import Optional, Tuple, Dict
from huggingface_hub import hf_hub_download, HfApi, snapshot_download
from huggingface_hub.utils import RepositoryNotFoundError, RevisionNotFoundError

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelDownloader:
    def __init__(self, cache_dir: Optional[str] = None, token: Optional[str] = None):
        """Initialize the model downloader with an optional cache directory and token."""
        self.cache_dir = cache_dir or os.path.expanduser("~/.cache/huggingface/hub")
        self.cache_dir = Path(self.cache_dir)
        self.token = token
        self.api = HfApi(token=token)
        self.verification_cache_file = self.cache_dir / "model_verification_cache.json"
        self.verification_cache = self._load_verification_cache()
        logger.info(f"ModelDownloader initialized with cache directory: {self.cache_dir}")
        if token:
            logger.info("Using provided Hugging Face token for authentication")
        
    def _load_verification_cache(self) -> Dict:
        """Load the verification cache from file."""
        try:
            if self.verification_cache_file.exists():
                with open(self.verification_cache_file, 'r') as f:
                    cache = json.load(f)
                logger.info("Loaded model verification cache")
                return cache
        except Exception as e:
            logger.warning(f"Error loading verification cache: {e}")
        return {}

    def _save_verification_cache(self):
        """Save the verification cache to file."""
        try:
            with open(self.verification_cache_file, 'w') as f:
                json.dump(self.verification_cache, f)
            logger.info("Saved model verification cache")
        except Exception as e:
            logger.warning(f"Error saving verification cache: {e}")

    def _get_model_cache_path(self, model_id: str) -> Path:
        """Convert model ID to cache directory path."""
        cache_name = f"models--{model_id.replace('/', '--')}"
        return self.cache_dir / cache_name

    def _setup_cache_structure(self, model_id: str, commit_hash: str) -> Tuple[Path, Path]:
        """Set up the cache directory structure for the model."""
        try:
            model_cache_path = self._get_model_cache_path(model_id)
            logger.info(f"Setting up cache structure for {model_id} at {model_cache_path}")
            
            # Create main model directory
            model_cache_path.mkdir(parents=True, exist_ok=True)
            
            # Create refs directory and main file
            refs_dir = model_cache_path / "refs"
            refs_dir.mkdir(exist_ok=True)
            main_file = refs_dir / "main"
            main_file.write_text(commit_hash)
            
            # Create snapshots directory and commit hash directory
            snapshots_dir = model_cache_path / "snapshots"
            snapshots_dir.mkdir(exist_ok=True)
            commit_dir = snapshots_dir / commit_hash
            commit_dir.mkdir(exist_ok=True)
            
            return model_cache_path, commit_dir
            
        except Exception as e:
            logger.error(f"Error setting up cache structure: {e}")
            raise

    def download_model(self, model_id: str) -> bool:
        """
        Download and set up a model in the Hugging Face cache directory.
        
        Args:
            model_id: The Hugging Face model ID (e.g., "Systran/faster-whisper-medium.en")
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info(f"Starting download of model: {model_id}")
        try:
            try:
                model_info = self.api.model_info(model_id)
                commit_hash = model_info.sha
                logger.info(f"Got model info with commit hash: {commit_hash}")
            except Exception as e:
                logger.error(f"Error getting model info: {e}")
                logger.info("Attempting alternative download method...")
                return self._download_model_alternative(model_id)

            model_cache_path, commit_dir = self._setup_cache_structure(model_id, commit_hash)
            essential_files = [
                "model.bin",
                "config.json",
                "tokenizer.json",
                "vocabulary.txt",
                "README.md"
            ]
            
            for filename in essential_files:
                try:
                    logger.info(f"Downloading {filename}...")
                    local_file = hf_hub_download(
                        repo_id=model_id,
                        filename=filename,
                        cache_dir=self.cache_dir,
                        local_dir=commit_dir,
                        local_dir_use_symlinks=False,
                        force_download=True,
                        token=self.token
                    )
                    
                    if Path(local_file).parent != commit_dir:
                        shutil.copy2(local_file, commit_dir / filename)
                        logger.info(f"Moved {filename} to correct location")
                        
                except (RepositoryNotFoundError, RevisionNotFoundError) as e:
                    if filename != "README.md":
                        logger.error(f"Error downloading {filename}: {e}")
                        return False
                    else:
                        logger.warning(f"README.md not found, continuing anyway")
            
            logger.info("Model download completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error downloading model {model_id}: {e}")
            return False

    def _download_model_alternative(self, model_id: str) -> bool:
        """Alternative download method using snapshot_download."""
        try:
            logger.info(f"Attempting alternative download for {model_id}")
            local_dir = snapshot_download(
                repo_id=model_id,
                cache_dir=self.cache_dir,
                local_dir=None,
                local_dir_use_symlinks=False,
                ignore_patterns=[".*", "*.md"],
                token=self.token
            )
            
            local_dir = Path(local_dir)
            commit_hash = local_dir.name.split("-")[-1]
            model_cache_path, commit_dir = self._setup_cache_structure(model_id, commit_hash)
            essential_files = ["model.bin", "config.json", "tokenizer.json", "vocabulary.txt"]
            
            for filename in essential_files:
                src_file = local_dir / filename
                if src_file.exists():
                    shutil.copy2(src_file, commit_dir / filename)
                    logger.info(f"Copied {filename} to cache structure")
                else:
                    logger.error(f"Required file {filename} not found in downloaded content")
                    return False
                    
            logger.info("Alternative download completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Alternative download failed: {e}")
            return False

    def verify_model_setup(self, model_id: str) -> bool:
        """Verify that a model is properly set up in the cache."""
        try:
            # Check cache first
            cache_key = f"{model_id}"
            if cache_key in self.verification_cache:
                cache_entry = self.verification_cache[cache_key]
                model_cache_path = self._get_model_cache_path(model_id)
                
                # Check if cache is still valid (model directory exists and has same commit hash)
                if model_cache_path.exists():
                    main_file = model_cache_path / "refs" / "main"
                    if main_file.exists():
                        current_commit = main_file.read_text().strip()
                        if current_commit == cache_entry.get('commit_hash'):
                            logger.info(f"Using cached verification result for {model_id}")
                            return True
                
                # Cache invalid, remove it
                del self.verification_cache[cache_key]
                self._save_verification_cache()

            # Perform full verification
            model_cache_path = self._get_model_cache_path(model_id)
            logger.info(f"Verifying model setup for {model_id} at {model_cache_path}")
            
            # Check if main model directory exists
            if not model_cache_path.exists():
                logger.info("Model cache path does not exist")
                return False
                
            # Check if refs/main exists and contains a commit hash
            main_file = model_cache_path / "refs" / "main"
            if not main_file.exists():
                logger.info("refs/main file does not exist")
                return False
                
            commit_hash = main_file.read_text().strip()
            if not commit_hash:
                logger.info("Empty commit hash in refs/main")
                return False
                
            # Check if commit directory exists with essential files
            commit_dir = model_cache_path / "snapshots" / commit_hash
            if not commit_dir.exists():
                logger.info(f"Commit directory does not exist: {commit_dir}")
                return False
                
            essential_files = ["model.bin", "config.json", "tokenizer.json", "vocabulary.txt"]
            missing_files = [f for f in essential_files if not (commit_dir / f).exists()]
            if missing_files:
                logger.info(f"Missing essential files: {missing_files}")
                return False
                
            # Cache the successful verification
            self.verification_cache[cache_key] = {
                'commit_hash': commit_hash,
                'verified_at': time.time()
            }
            self._save_verification_cache()
            
            logger.info("Model setup verified successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error verifying model setup: {e}")
            return False 