# Icon and Resource Discovery Architecture

## 1. Overview

This document describes the architecture and design for a generic resource discovery system that supports SVG icons, raster images, and future extensibility to other resource types (audio, video, etc.). The system combines bundled resource discovery with extensible resource pack discovery via Python EntryPoints.

### 1.1 Purpose

The resource discovery system provides a unified interface for locating and resolving resources across multiple sources:

1. **Bundled Resources**: Application-local resources (SVG icons, images, etc.)
2. **Resource Packs**: Third-party resource packages discovered via Python EntryPoints
3. **System Resources**: Platform-specific system resources (future consideration)

The system is designed to be generic enough to support multiple resource types while providing specialized support for SVG icon libraries.

### 1.2 Core Value Proposition

- **Generic Framework**: Unified interface for multiple resource types (SVG, raster images, future: audio/video)
- **Extensible**: Resource packs can be added via standard Python EntryPoints mechanism
- **Icon-Focused**: Specialized support for SVG icon libraries (Lucide, Feather, Material Design Icons, etc.)
- **Prefix-Based Resolution**: Namespace disambiguation via `pack:name` format
- **Efficient**: Lazy loading with caching support

### 1.3 Influences & Similar Systems

- **Iconify**: Universal icon framework with unified API for multiple icon libraries
- **react-icons**: React component library aggregating multiple icon sets
- **FreeDesktop Icon Theme Spec**: Hierarchical icon lookup with theme inheritance and size matching
- **Material Design Icons**: Structured icon library with variants and metadata
- **Lucide Icons**: Modern icon library with consistent design and SVG format

## 2. Architecture Overview

The resource discovery system follows a provider-based architecture:

```
┌─────────────────────────────────────────────────────────┐
│              Resource Registry                           │
│  (Unified interface for resource lookup and resolution)  │
└─────────────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Resource   │ │   Resource   │ │   Resource   │
│  Providers   │ │   Providers  │ │   Providers  │
│  (SVG Icons) │ │  (Raster)    │ │  (Future)    │
└──────────────┘ └──────────────┘ └──────────────┘
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ EntryPoints  │ │ importlib.   │ │   Protocol   │
│ mechanism    │ │ resources    │ │   Interface  │
└──────────────┘ └──────────────┘ └──────────────┘
```

### 2.1 Resource Types

The system supports multiple resource types through a common provider interface:

1. **SVG Icons**: Vector graphics for icons (primary use case)
2. **Raster Images**: PNG, JPEG, WebP images
3. **Future Types**: Audio files, video files, 3D models, etc.

Each resource type implements the `ResourceProvider` protocol, allowing the registry to handle them uniformly while providing type-specific functionality.

## 3. Resource Provider Protocol

The core abstraction is the `ResourceProvider` protocol, which defines how resources are discovered and retrieved.

### 3.1 Protocol Definition

```python
from typing import Protocol, BinaryIO

class ResourceProvider(Protocol):
    """Protocol for resource providers.
    
    Resource providers implement this protocol to supply resources
    (SVG icons, images, etc.) to the resource registry.
    """
    
    def get_resource(self, key: object) -> str | bytes:
        """Get resource content for a key.
        
        Args:
            key: A resource key object (pack-specific or generic)
            
        Returns:
            Resource content as string (for text-based like SVG) or bytes (for binary)
            
        Raises:
            ValueError: If the resource cannot be found
        """
        ...
    
    def list_resources(self) -> Iterator[str]:
        """List all available resource names/identifiers.
        
        Returns:
            Iterator of resource names/identifiers
        """
        ...
    
    def get_metadata(self, key: object) -> dict[str, Any] | None:
        """Get metadata for a resource.
        
        Args:
            key: A resource key object
            
        Returns:
            Dictionary of metadata (name, dimensions, variants, etc.) or None
        """
        ...
```

### 3.2 Specialized Protocols

For icon-specific use cases, a more specialized protocol can be defined:

```python
class IconProvider(ResourceProvider, Protocol):
    """Protocol for SVG icon providers."""
    
    def get_svg(self, key: object) -> str:
        """Get SVG content for an icon key.
        
        This is a convenience method that calls get_resource() and
        ensures the result is a string (SVG content).
        """
        ...
    
    def get_icon_metadata(self, name: str) -> IconMetadata | None:
        """Get metadata for a specific icon.
        
        Returns:
            IconMetadata with name, dimensions, variants, etc.
        """
        ...
```

## 4. Resource Pack Discovery

Resource packs are third-party packages that provide resources via Python EntryPoints.

### 4.1 EntryPoints Mechanism

Resource packs register themselves using the EntryPoints mechanism (`importlib.metadata.entry_points`).

**Entry Point Group**: `resourcepacks` (or project-specific like `myproject.resourcepacks`)

**Entry Point Format**: Factory function that returns a provider instance and metadata

### 4.2 Resource Pack Structure

A resource pack package should define an entry point in its `setup.py` or `pyproject.toml`:

**setup.py**:
```python
setup(
    name="my-icon-pack",
    entry_points={
        "resourcepacks": [
            "my-icon-pack = my_icon_pack:get_resource_provider",
        ],
    },
)
```

**pyproject.toml**:
```toml
[project.entry-points."resourcepacks"]
"my-icon-pack" = "my_icon_pack:get_resource_provider"
```

### 4.3 Resource Pack Implementation

The entry point factory function returns a provider instance and optional metadata:

```python
# my_icon_pack/__init__.py
from my_icon_pack.provider import MyIconProvider

def get_resource_provider():
    """Entry point factory returning resource provider."""
    # Option 1: Return provider instance
    return MyIconProvider()
    
    # Option 2: Return tuple with provider and metadata
    # return (MyIconProvider(), {"prefix": "myicons", "version": "1.0.0"})
    
    # Option 3: Return tuple with provider, key_type, and prefixes
    # return (MyIconKey, MyIconProvider(), ["myicons", "mi"])
```

### 4.4 Discovery Implementation

```python
class ResourceRegistry:
    """Registry for resource providers."""
    
    def __init__(self) -> None:
        self._providers: dict[Type[Any], ResourceProvider] = {}
        self._prefixes: dict[str, Type[Any]] = {}
        self._loaded = False
    
    def _load_entry_points(self) -> None:
        """Load resource packs from entry points."""
        if self._loaded:
            return
        
        try:
            from importlib.metadata import entry_points
            eps = entry_points(group="resourcepacks")
        except ImportError:
            # Python < 3.10 fallback
            try:
                import importlib_metadata
                eps = importlib_metadata.entry_points(group="resourcepacks")
            except ImportError:
                return
        
        for ep in eps:
            try:
                factory = ep.load()
                result = factory()
                
                # Handle various return types
                if isinstance(result, tuple) and len(result) >= 2:
                    key_type, provider = result[0], result[1]
                    prefixes = result[2] if len(result) > 2 else None
                    self.register(key_type, provider, prefixes)
                elif isinstance(result, ResourceProvider):
                    # Generic provider without key type
                    self.register_generic(ep.name, result)
            except Exception as e:
                import warnings
                warnings.warn(f"Failed to load resource pack {ep.name}: {e}")
                continue
        
        self._loaded = True
```

## 5. SVG Icon Discovery

SVG icons are the primary use case, with specialized support for icon libraries.

### 5.1 Icon Key Types

Icon keys represent requests for specific icons. They can be:

1. **Pack-Specific Keys**: Type-safe keys for specific icon packs (e.g., `LucideIconKey`)
2. **Generic Keys**: Generic keys that resolve via prefix (e.g., `SvgIconKey` with `ref="lucide:lightbulb"`)

#### Pack-Specific Key Example

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class LucideIconKey:
    """Lucide icon key."""
    
    pack_id: str = "lucide"
    pack_version: str = "v1"
    name: str  # e.g., "lightbulb"
    w: int | float  # Width
    h: int | float  # Height
    tint: str | None = None
    stroke_width: float | None = None
    variant: str | None = None
```

#### Generic Key Example

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class SvgIconKey:
    """Generic SVG icon key with prefix-based resolution."""
    
    ref: str  # "pack:name" or direct reference
    w: int | float
    h: int | float
    tint: str | None = None
    variant: str | None = None
    
    def resolve_ref(self) -> tuple[str, str] | None:
        """Resolve prefix:name format to (prefix, name)."""
        if ":" in self.ref:
            parts = self.ref.split(":", 1)
            return (parts[0], parts[1])
        return None
```

### 5.2 Prefix-Based Resolution

Icons can be referenced using a `pack:name` format for namespace disambiguation:

- `lucide:lightbulb` - Lucide icon named "lightbulb"
- `feather:home` - Feather icon named "home"
- `material:settings` - Material Design icon named "settings"

The registry resolves prefixes to pack-specific key types:

```python
def resolve_icon_key(key: SvgIconKey) -> Any:
    """Resolve a generic SvgIconKey to a pack-specific icon key."""
    resolved = key.resolve_ref()
    if not resolved:
        return key  # No prefix, return as-is
    
    prefix, name = resolved
    registry = get_default_registry()
    key_type = registry.resolve_prefix(prefix)
    
    if key_type is None:
        return key  # Unknown prefix
    
    # Create pack-specific key
    return key_type(
        name=name,
        w=key.w,
        h=key.h,
        tint=key.tint,
        variant=key.variant,
    )
```

### 5.3 Icon Provider Implementation

Example implementation for Lucide icons:

```python
class LucideRenderer(ResourceProvider):
    """Renderer for Lucide icons."""
    
    def get_resource(self, key: object) -> str:
        """Get SVG content for a Lucide icon key."""
        if not isinstance(key, LucideIconKey):
            raise ValueError(f"Expected LucideIconKey, got {type(key)}")
        
        try:
            from lucide import lucide_icon
        except ImportError:
            raise ValueError("python-lucide package not installed")
        
        # Get the icon SVG
        svg_content = lucide_icon(key.name)
        if not svg_content:
            raise ValueError(f"Lucide icon '{key.name}' not found")
        
        # Apply transformations (tint, stroke width, etc.)
        svg_content = self._apply_transformations(svg_content, key)
        
        return svg_content
    
    def _apply_transformations(self, svg: str, key: LucideIconKey) -> str:
        """Apply transformations to SVG content."""
        # Apply tinting
        if key.tint:
            svg = svg.replace('stroke="currentColor"', f'stroke="{key.tint}"')
            svg = svg.replace('fill="currentColor"', f'fill="{key.tint}"')
        
        # Apply stroke width
        if key.stroke_width is not None:
            svg = svg.replace('stroke-width="2"', f'stroke-width="{key.stroke_width}"')
        
        return svg
    
    def list_resources(self) -> Iterator[str]:
        """List all available Lucide icon names."""
        try:
            from lucide import icon_names
            yield from icon_names()
        except ImportError:
            pass
    
    def get_metadata(self, key: object) -> dict[str, Any] | None:
        """Get metadata for a Lucide icon."""
        if not isinstance(key, LucideIconKey):
            return None
        
        return {
            "pack": "lucide",
            "name": key.name,
            "width": key.w,
            "height": key.h,
            "tint": key.tint,
            "stroke_width": key.stroke_width,
        }
```

### 5.4 Icon Library Patterns

Different icon libraries follow different patterns:

**Lucide Icons**:
- Python package: `lucide-python`
- Function-based: `lucide_icon(name)` returns SVG string
- Consistent stroke-based design

**Feather Icons**:
- Similar to Lucide (forked from Feather)
- SVG files in package
- File-based lookup

**Material Design Icons**:
- Multiple variants (filled, outlined, rounded, sharp)
- Organized by category
- Metadata-rich (tags, categories, etc.)

**Font Awesome**:
- Icon font and SVG versions
- Extensive icon set
- Versioned releases

## 6. Resource Registry Pattern

The resource registry provides a unified interface for resource lookup and resolution.

### 6.1 Registry Implementation

```python
class ResourceRegistry:
    """Registry for resource providers."""
    
    def __init__(self) -> None:
        self._providers: dict[Type[Any], ResourceProvider] = {}
        self._prefixes: dict[str, Type[Any]] = {}
        self._generic_providers: dict[str, ResourceProvider] = {}
        self._loaded = False
    
    def register(
        self,
        key_type: Type[Any],
        provider: ResourceProvider,
        prefixes: list[str] | None = None,
    ) -> None:
        """Register a resource provider for a key type.
        
        Args:
            key_type: The resource key class (e.g., LucideIconKey)
            provider: The provider instance
            prefixes: Optional list of prefixes (e.g., ["lucide"]) for string-based resolution
        """
        self._providers[key_type] = provider
        if prefixes:
            for prefix in prefixes:
                self._prefixes[prefix.lower()] = key_type
    
    def get_provider(self, key: object) -> ResourceProvider | None:
        """Get the provider for a resource key.
        
        Args:
            key: The resource key object
            
        Returns:
            The provider instance, or None if not found
        """
        self._load_entry_points()
        key_type = type(key)
        return self._providers.get(key_type)
    
    def resolve_prefix(self, prefix: str) -> Type[Any] | None:
        """Resolve a prefix to a resource key type.
        
        Args:
            prefix: The prefix (e.g., "lucide")
            
        Returns:
            The resource key type, or None if not found
        """
        self._load_entry_points()
        return self._prefixes.get(prefix.lower())
    
    def get_resource(self, key: object) -> str | bytes:
        """Get resource content for a key.
        
        Args:
            key: A resource key object
            
        Returns:
            Resource content as string or bytes
            
        Raises:
            ValueError: If the resource cannot be found
        """
        provider = self.get_provider(key)
        if provider is None:
            raise ValueError(f"No provider found for key type: {type(key)}")
        
        return provider.get_resource(key)
```

### 6.2 Factory Functions

```python
_default_registry: ResourceRegistry | None = None

def get_default_registry() -> ResourceRegistry:
    """Get the default global resource registry instance."""
    global _default_registry
    if _default_registry is None:
        _default_registry = ResourceRegistry()
    return _default_registry

def register_resource_provider(
    key_type: Type[Any],
    provider: ResourceProvider,
    prefixes: list[str] | None = None,
) -> None:
    """Register a resource provider (convenience function)."""
    registry = get_default_registry()
    registry.register(key_type, provider, prefixes)
```

## 7. Metadata and Versioning

Resources and resource packs can include metadata for versioning, validation, and discovery.

### 7.1 Resource Metadata

```python
@dataclass(frozen=True)
class ResourceMetadata:
    """Metadata for a resource."""
    
    name: str
    pack: str
    pack_version: str
    resource_type: str  # "svg", "png", "audio", etc.
    dimensions: tuple[int, int] | None = None
    variants: list[str] | None = None
    tags: list[str] | None = None
    description: str | None = None
```

### 7.2 Pack Metadata

```python
@dataclass(frozen=True)
class PackMetadata:
    """Metadata for a resource pack."""
    
    name: str
    version: str
    prefixes: list[str]
    resource_type: str
    resource_count: int
    description: str | None = None
    author: str | None = None
    license: str | None = None
```

### 7.3 Versioning Strategy

- **Pack Versioning**: Resource packs declare versions in their entry point metadata
- **Resource Versioning**: Resources can include version information in metadata
- **API Versioning**: Registry API can include version fields for compatibility

## 8. Extensibility

The system is designed to be extensible to new resource types and formats.

### 8.1 Adding New Resource Types

To add support for a new resource type (e.g., raster images):

1. **Define Resource Key Type**:
```python
@dataclass(frozen=True, slots=True, kw_only=True)
class ImageResourceKey:
    """Key for raster image resources."""
    pack: str
    name: str
    format: str  # "png", "jpg", "webp"
    target_size: tuple[int, int] | None = None
```

2. **Implement Resource Provider**:
```python
class ImageResourceProvider(ResourceProvider):
    """Provider for raster image resources."""
    
    def get_resource(self, key: object) -> bytes:
        """Get image bytes."""
        if not isinstance(key, ImageResourceKey):
            raise ValueError(f"Expected ImageResourceKey, got {type(key)}")
        
        # Load image from pack
        image_path = self._get_image_path(key)
        with open(image_path, "rb") as f:
            return f.read()
    
    def get_metadata(self, key: object) -> dict[str, Any] | None:
        """Get image metadata."""
        # Return dimensions, format, etc.
        ...
```

3. **Register Provider**:
```python
registry.register(ImageResourceKey, ImageResourceProvider(), ["img", "image"])
```

### 8.2 Adding New Formats

New formats can be added by:

1. Extending the `ResourceProvider` protocol with format-specific methods
2. Implementing format-specific providers
3. Adding format detection and routing logic to the registry

### 8.3 Future Resource Types

**Audio Resources**:
- Audio files (MP3, OGG, WAV)
- Sound effects, music tracks
- Metadata: duration, format, sample rate

**Video Resources**:
- Video files (MP4, WebM)
- Animated content
- Metadata: duration, resolution, codec

**3D Models**:
- 3D model files (GLTF, OBJ)
- Mesh data, textures
- Metadata: vertices, materials, animations

## 9. Best Practices

### 9.1 Lessons from Existing Solutions

**Iconify**:
- Unified API across multiple icon libraries
- Lazy loading and caching
- Icon transformation (size, color, rotation)
- Icon search and discovery

**react-icons**:
- Aggregates multiple icon sets
- Tree-shaking support
- Consistent API across libraries
- TypeScript type definitions

**FreeDesktop Icon Theme Spec**:
- Hierarchical lookup with theme inheritance
- Size matching and fallback
- Context-based icon selection
- Scalable icon formats

**Material Design Icons**:
- Structured metadata (tags, categories)
- Multiple variants per icon
- Consistent design language
- Versioned releases

### 9.2 Implementation Recommendations

1. **Lazy Loading**: Load resource packs only when needed
2. **Caching**: Cache resource content and metadata
3. **Error Handling**: Gracefully handle missing resources and invalid packs
4. **Extensibility**: Use protocols and EntryPoints for extensibility
5. **Type Safety**: Provide type-safe key classes for pack-specific resources
6. **Prefix Resolution**: Support both type-safe and string-based resource references

### 9.3 Performance Considerations

- **Lazy Discovery**: Load entry points only when registry is accessed
- **Resource Caching**: Cache frequently accessed resources
- **Lazy Resource Loading**: Load resource content only when requested
- **Parallel Loading**: Consider parallel resource pack discovery for large installations

### 9.4 Resource Bundling Strategies

**Package-Based**:
- Resources bundled in Python package
- Accessed via `importlib.resources`
- Versioned with package version

**External Files**:
- Resources in separate directory
- Referenced via path configuration
- Can be updated independently

**Remote Resources**:
- Resources fetched from CDN or API
- Cached locally
- Versioned via URL or metadata

## 10. SVG Icon Specifics

### 10.1 SVG Transformation

SVG icons often need transformation before use:

- **Tinting**: Replace `currentColor` or specific colors
- **Sizing**: Adjust viewBox and dimensions
- **Stroke Width**: Modify stroke-width attribute
- **Rotation**: Apply transform attribute
- **Opacity**: Adjust opacity or fill-opacity

### 10.2 SVG Optimization

Consider SVG optimization:

- Remove unnecessary attributes
- Minimize path data
- Remove metadata and comments
- Optimize viewBox

### 10.3 SVG Rendering

SVG content must be rendered to raster format for display:

- **CairoSVG**: Python library for SVG to PNG/PDF conversion
- **Pillow**: Limited SVG support (read-only)
- **Custom Renderer**: Implement custom SVG rendering pipeline

Example rendering pipeline:

```python
def render_svg_icon(key: SvgIconKey) -> Image.Image:
    """Render SVG icon to PIL Image."""
    # Resolve icon key
    resolved_key = resolve_icon_key(key)
    
    # Get SVG content
    registry = get_default_registry()
    svg_content = registry.get_resource(resolved_key)
    
    # Render SVG to PNG bytes
    import cairosvg
    png_bytes = cairosvg.svg2png(
        bytestring=svg_content.encode("utf-8"),
        output_width=key.w,
        output_height=key.h,
    )
    
    # Load PNG bytes into PIL Image
    from PIL import Image
    import io
    image = Image.open(io.BytesIO(png_bytes))
    return image.convert("RGBA")
```

## 11. Raster Image Resources

### 11.1 Image Resource Keys

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class ImageResourceKey:
    """Key for raster image resources."""
    
    pack: str
    name: str
    format: str = "png"  # "png", "jpg", "webp", etc.
    target_size: tuple[int, int] | None = None
    resize_mode: str = "fit"  # "fit", "crop", "stretch"
```

### 11.2 Image Provider

```python
class ImageResourceProvider(ResourceProvider):
    """Provider for raster image resources."""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
    
    def get_resource(self, key: object) -> bytes:
        """Get image bytes."""
        if not isinstance(key, ImageResourceKey):
            raise ValueError(f"Expected ImageResourceKey, got {type(key)}")
        
        image_path = self.base_path / f"{key.name}.{key.format}"
        
        if not image_path.exists():
            raise ValueError(f"Image not found: {image_path}")
        
        # Optionally resize image
        if key.target_size:
            from PIL import Image
            img = Image.open(image_path)
            img = self._resize_image(img, key.target_size, key.resize_mode)
            
            # Convert to bytes
            import io
            buffer = io.BytesIO()
            img.save(buffer, format=key.format.upper())
            return buffer.getvalue()
        
        # Return original image bytes
        with open(image_path, "rb") as f:
            return f.read()
    
    def _resize_image(
        self,
        img: Image.Image,
        target_size: tuple[int, int],
        mode: str,
    ) -> Image.Image:
        """Resize image according to mode."""
        if mode == "fit":
            img.thumbnail(target_size, Image.Resampling.LANCZOS)
        elif mode == "crop":
            img = img.resize(target_size, Image.Resampling.LANCZOS)
        elif mode == "stretch":
            img = img.resize(target_size, Image.Resampling.LANCZOS)
        return img
```

## 12. Future Considerations

### 12.1 Audio Resources

Support for audio files:

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class AudioResourceKey:
    """Key for audio resources."""
    
    pack: str
    name: str
    format: str = "mp3"  # "mp3", "ogg", "wav"
    start_time: float | None = None  # Start offset in seconds
    duration: float | None = None  # Duration in seconds
```

### 12.2 Video Resources

Support for video files:

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class VideoResourceKey:
    """Key for video resources."""
    
    pack: str
    name: str
    format: str = "mp4"  # "mp4", "webm"
    target_size: tuple[int, int] | None = None
    start_time: float | None = None
    duration: float | None = None
```

### 12.3 Resource Transformation Pipelines

Support for resource transformation:

- **Image Processing**: Resize, crop, filter, watermark
- **Audio Processing**: Trim, normalize, convert format
- **Video Processing**: Transcode, resize, extract frames
- **SVG Processing**: Optimize, minify, transform

### 12.4 Resource Validation

Add resource validation and integrity checks:

- **Format Validation**: Verify resource format matches declared type
- **Integrity Checks**: Verify resource hasn't been corrupted
- **Metadata Validation**: Verify metadata matches resource content
- **Version Compatibility**: Check resource pack version compatibility

### 12.5 Resource Search and Discovery

Add resource search capabilities:

- **Name Search**: Search resources by name
- **Tag Search**: Search resources by tags
- **Category Search**: Search resources by category
- **Metadata Search**: Search resources by metadata fields

## 13. Migration from deckr Prototype

The deckr prototype (`deckr/render/iconpacks/`) provides a working implementation that can be extracted and generalized.

### 13.1 Key Components to Extract

- `_registry.py`: Resource registry and EntryPoints discovery
- `_protocol.py`: Resource provider protocol definition
- `_resolver.py`: Prefix-based resolution logic
- `_lucide.py`: Lucide icon pack implementation (reference)

### 13.2 Changes for Generic Framework

1. **Generalize Protocol**: Rename `IconKeyRenderer` to `ResourceProvider`
2. **Support Multiple Types**: Extend registry to handle multiple resource types
3. **Entry Point Group**: Change from `deckr.iconpacks` to project-specific group
4. **Package Structure**: Reorganize as standalone package
5. **API Stability**: Define stable public API

### 13.3 Backward Compatibility

If maintaining compatibility with deckr:

- Support both `deckr.iconpacks` and new entry point group
- Provide migration guide for icon pack authors
- Maintain API compatibility where possible

## 14. Example Usage

### 14.1 Basic Icon Usage

```python
from resourcediscovery import ResourceRegistry, get_default_registry
from resourcediscovery.keys import SvgIconKey

# Get default registry
registry = get_default_registry()

# Create icon key with prefix
icon_key = SvgIconKey(
    ref="lucide:lightbulb",
    w=24,
    h=24,
    tint="#FF0000",
)

# Get SVG content
svg_content = registry.get_resource(icon_key)
print(svg_content)  # SVG string
```

### 14.2 Pack-Specific Icon Usage

```python
from resourcediscovery.keys import LucideIconKey
from resourcediscovery.providers import LucideRenderer

# Create pack-specific key
icon_key = LucideIconKey(
    name="lightbulb",
    w=24,
    h=24,
    tint="#FF0000",
    stroke_width=2.0,
)

# Get provider and retrieve SVG
registry = get_default_registry()
provider = registry.get_provider(icon_key)
svg_content = provider.get_resource(icon_key)
```

### 14.3 Image Resource Usage

```python
from resourcediscovery.keys import ImageResourceKey

# Create image key
image_key = ImageResourceKey(
    pack="my-images",
    name="logo",
    format="png",
    target_size=(200, 200),
    resize_mode="fit",
)

# Get image bytes
registry = get_default_registry()
image_bytes = registry.get_resource(image_key)

# Use with PIL
from PIL import Image
import io
img = Image.open(io.BytesIO(image_bytes))
```

### 14.4 Resource Pack Implementation

```python
# my_icon_pack/__init__.py
from my_icon_pack.provider import MyIconProvider
from my_icon_pack.keys import MyIconKey

def get_resource_provider():
    """Entry point factory for icon pack."""
    return (MyIconKey, MyIconProvider(), ["myicons", "mi"])

# setup.py or pyproject.toml
# [project.entry-points."resourcepacks"]
# "my-icon-pack" = "my_icon_pack:get_resource_provider"
```

## 15. Comparison with Existing Solutions

| Feature | This Design | Iconify | react-icons | FreeDesktop |
|---------|-------------|---------|-------------|-------------|
| SVG Icons | ✅ | ✅ | ✅ | ✅ |
| Raster Images | ✅ | ❌ | ❌ | ✅ |
| EntryPoints | ✅ | ❌ | ❌ | ❌ |
| Prefix Resolution | ✅ | ✅ | ❌ | ❌ |
| Multiple Formats | ✅ | ❌ | ❌ | ✅ |
| Extensible | ✅ | ✅ | ❌ | ✅ |
| Language | Python | JS/TS | JS/TS | C/Spec |

**Key Differentiators**:
- Generic resource framework (not icon-specific)
- Python-native with EntryPoints extensibility
- Support for multiple resource types (SVG, raster, future: audio/video)
- Prefix-based namespace resolution
- Designed for standalone project extraction

