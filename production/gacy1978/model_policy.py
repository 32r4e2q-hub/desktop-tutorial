"""Free Zhipu model is the single source of truth; no alternate provider fallback."""
COGVIDEOX_MODEL = 'cogvideox-flash'
MODEL = COGVIDEOX_MODEL
FREE_MODEL = COGVIDEOX_MODEL
SIZE_TIER = '720P'
ALLOWED_MODELS = (COGVIDEOX_MODEL,)
# Positive visible-content constraints; no automatic obfuscation on moderation rejection.
PROMPT_GUARDRAILS = (
    'Fictional fully clothed stylized adult cast, respectful non-graphic documentary reenactment; '
    'anonymous younger figures are back silhouettes only; plain unlettered props and surfaces. '
    'Physical movement continues naturally within one coherent shot, consistent faces and anatomy. '
    'One continuous scene with a single smooth camera move; clear lower subtitle safety area.'
)
# Legacy validator schema compatibility only, never sent to another video provider.
SUPPORTED_SIZES = ('720P','1080P','1K','2K')
SUPPORTED_MODES = ('text','keyframe','reference')
