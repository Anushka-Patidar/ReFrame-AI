from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ReFrame API"
    api_prefix: str = "/api"
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_database: str = "reframe"
    frontend_origins: str = "http://localhost:5173,http://127.0.0.1:5173,null"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"

    # Local-only room redesign (no paid image APIs required).
    image_provider: str = "local"
    # Model id is configuration-only — do not hard-code elsewhere.
    local_model_id: str = "segmind/tiny-sd"
    # Backward-compatible alias read by older .env files.
    local_diffusion_model: str = "segmind/tiny-sd"
    # auto | low_memory | balanced | high
    local_ai_profile: str = "auto"
    # Inpainting model (used when edit masks exist).
    local_inpainting_model_id: str = "runwayml/stable-diffusion-inpainting"
    # Single ControlNet model for architecture-preserving SD1.5 generation.
    local_controlnet_canny_model_id: str = "lllyasviel/control_v11p_sd15_canny"
    # Bounded generate → validate → retry attempts inside the pipeline.
    local_max_retries: int = 2
    # Optional manual overrides (0 = use profile defaults).
    local_image_width: int = 0
    local_image_height: int = 0
    local_inference_steps: int = 0
    local_guidance_scale: float = 0.0
    local_structure_strength: float = 0.0

    # Development-only: validate and log region-mask / structure pipeline.
    debug_mask_pipeline: bool = False
    debug_mask_visual_preview: bool = False

    # Optional chat improvements only (not required for redesign).
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-20250514"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


def get_frontend_origins() -> list[str]:
    return [origin.strip() for origin in settings.frontend_origins.split(",") if origin.strip()]
