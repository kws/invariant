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
- **Discovery Focus**: This library discovers and retrieves resources. How those resources are used (rendered, cached, transformed) is the responsibility of the consuming application.

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
    
    def get_resource(self, descriptor: object) -> str | bytes:
        """Get resource content for a descriptor.
        
        Args:
            descriptor: A resource descriptor object (pack-specific or generic)
            
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
    
    def get_metadata(self, descriptor: object) -> dict[str, Any] | None:
        """Get metadata for a resource.
        
        Args:
            descriptor: A resource descriptor object
            
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
    
    def get_svg(self, descriptor: object) -> str:
        """Get SVG content for an icon descriptor.
        
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
                    descriptor_type, provider = result[0], result[1]
                    prefixes = result[2] if len(result) > 2 else None
                    self.register(descriptor_type, provider, prefixes)
                elif isinstance(result, ResourceProvider):
                    # Generic provider without descriptor type
                    self.register_generic(ep.name, result)
            except Exception as e:
                import warnings
                warnings.warn(f"Failed to load resource pack {ep.name}: {e}")
                continue
        
        self._loaded = True
```

## 5. SVG Icon Discovery

SVG icons are the primary use case, with specialized support for icon libraries.

### 5.1 Icon Descriptor Types

Icon descriptors represent requests for specific icons. They can be:

1. **Pack-Specific Descriptors**: Type-safe descriptors for specific icon packs (e.g., `LucideIconDescriptor`)
2. **Generic Descriptors**: Generic descriptors that resolve via prefix (e.g., `SvgIconDescriptor` with `ref="lucide:lightbulb"`)

#### Pack-Specific Descriptor Example

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class LucideIconDescriptor:
    """Lucide icon descriptor."""
    
    pack_id: str = "lucide"
    pack_version: str = "v1"
    name: str  # e.g., "lightbulb"
    w: int | float  # Width (hint for transformations, not rendering instruction)
    h: int | float  # Height (hint for transformations, not rendering instruction)
    tint: str | None = None  # Optional SVG string transformation hint
    stroke_width: float | None = None  # Optional SVG string transformation hint
    variant: str | None = None
```

#### Generic Descriptor Example

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class SvgIconDescriptor:
    """Generic SVG icon descriptor with prefix-based resolution."""
    
    ref: str  # "pack:name" or direct reference
    w: int | float  # Width (hint for transformations, not rendering instruction)
    h: int | float  # Height (hint for transformations, not rendering instruction)
    tint: str | None = None  # Optional SVG string transformation hint
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

The registry resolves prefixes to pack-specific descriptor types:

```python
def resolve_icon_descriptor(descriptor: SvgIconDescriptor) -> Any:
    """Resolve a generic SvgIconDescriptor to a pack-specific icon descriptor."""
    resolved = descriptor.resolve_ref()
    if not resolved:
        return descriptor  # No prefix, return as-is
    
    prefix, name = resolved
    registry = get_default_registry()
    descriptor_type = registry.resolve_prefix(prefix)
    
    if descriptor_type is None:
        return descriptor  # Unknown prefix
    
    # Create pack-specific descriptor
    return descriptor_type(
        name=name,
        w=descriptor.w,
        h=descriptor.h,
        tint=descriptor.tint,
        variant=descriptor.variant,
    )
```

### 5.3 Icon Provider Implementation

Example implementation for Lucide icons:

```python
class LucideProvider(ResourceProvider):
    """Provider for Lucide icons."""
    
    def get_resource(self, descriptor: object) -> str:
        """Get SVG content for a Lucide icon descriptor."""
        if not isinstance(descriptor, LucideIconDescriptor):
            raise ValueError(f"Expected LucideIconDescriptor, got {type(descriptor)}")
        
        try:
            from lucide import lucide_icon
        except ImportError:
            raise ValueError("python-lucide package not installed")
        
        # Get the icon SVG
        svg_content = lucide_icon(descriptor.name)
        if not svg_content:
            raise ValueError(f"Lucide icon '{descriptor.name}' not found")
        
        # Apply optional SVG string transformations (tint, stroke width, etc.)
        svg_content = self._apply_transformations(svg_content, descriptor)
        
        return svg_content
    
    def _apply_transformations(self, svg: str, descriptor: LucideIconDescriptor) -> str:
        """Apply optional transformations to SVG string content.
        
        Transformations modify the SVG string itself before returning it.
        These are NOT rendering instructions - they change the SVG content.
        """
        # Apply tinting (replace currentColor with specific color)
        if descriptor.tint:
            svg = svg.replace('stroke="currentColor"', f'stroke="{descriptor.tint}"')
            svg = svg.replace('fill="currentColor"', f'fill="{descriptor.tint}"')
        
        # Apply stroke width (modify stroke-width attribute)
        if descriptor.stroke_width is not None:
            svg = svg.replace('stroke-width="2"', f'stroke-width="{descriptor.stroke_width}"')
        
        return svg
    
    def list_resources(self) -> Iterator[str]:
        """List all available Lucide icon names."""
        try:
            from lucide import icon_names
            yield from icon_names()
        except ImportError:
            pass
    
    def get_metadata(self, descriptor: object) -> dict[str, Any] | None:
        """Get metadata for a Lucide icon."""
        if not isinstance(descriptor, LucideIconDescriptor):
            return None
        
        return {
            "pack": "lucide",
            "name": descriptor.name,
            "width_hint": descriptor.w,
            "height_hint": descriptor.h,
            "tint": descriptor.tint,
            "stroke_width": descriptor.stroke_width,
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
        descriptor_type: Type[Any],
        provider: ResourceProvider,
        prefixes: list[str] | None = None,
    ) -> None:
        """Register a resource provider for a descriptor type.
        
        Args:
            descriptor_type: The resource descriptor class (e.g., LucideIconDescriptor)
            provider: The provider instance
            prefixes: Optional list of prefixes (e.g., ["lucide"]) for string-based resolution
        """
        self._providers[descriptor_type] = provider
        if prefixes:
            for prefix in prefixes:
                self._prefixes[prefix.lower()] = descriptor_type
    
    def get_provider(self, descriptor: object) -> ResourceProvider | None:
        """Get the provider for a resource descriptor.
        
        Args:
            descriptor: The resource descriptor object
            
        Returns:
            The provider instance, or None if not found
        """
        self._load_entry_points()
        descriptor_type = type(descriptor)
        return self._providers.get(descriptor_type)
    
    def resolve_prefix(self, prefix: str) -> Type[Any] | None:
        """Resolve a prefix to a resource descriptor type.
        
        Args:
            prefix: The prefix (e.g., "lucide")
            
        Returns:
            The resource descriptor type, or None if not found
        """
        self._load_entry_points()
        return self._prefixes.get(prefix.lower())
    
    def get_resource(self, descriptor: object) -> str | bytes:
        """Get resource content for a descriptor.
        
        Args:
            descriptor: A resource descriptor object
            
        Returns:
            Resource content as string or bytes
            
        Raises:
            ValueError: If the resource cannot be found
        """
        provider = self.get_provider(descriptor)
        if provider is None:
            raise ValueError(f"No provider found for descriptor type: {type(descriptor)}")
        
        return provider.get_resource(descriptor)
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
    descriptor_type: Type[Any],
    provider: ResourceProvider,
    prefixes: list[str] | None = None,
) -> None:
    """Register a resource provider (convenience function)."""
    registry = get_default_registry()
    registry.register(descriptor_type, provider, prefixes)
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

1. **Define Resource Descriptor Type**:
```python
@dataclass(frozen=True, slots=True, kw_only=True)
class ImageResourceDescriptor:
    """Descriptor for raster image resources."""
    pack: str
    name: str
    format: str  # "png", "jpg", "webp"
    target_size: tuple[int, int] | None = None  # Optional hint for transformations
```

2. **Implement Resource Provider**:
```python
class ImageResourceProvider(ResourceProvider):
    """Provider for raster image resources."""
    
    def get_resource(self, descriptor: object) -> bytes:
        """Get image bytes."""
        if not isinstance(descriptor, ImageResourceDescriptor):
            raise ValueError(f"Expected ImageResourceDescriptor, got {type(descriptor)}")
        
        # Load image from pack
        image_path = self._get_image_path(descriptor)
        with open(image_path, "rb") as f:
            return f.read()
    
    def get_metadata(self, descriptor: object) -> dict[str, Any] | None:
        """Get image metadata."""
        # Return dimensions, format, etc.
        ...
```

3. **Register Provider**:
```python
registry.register(ImageResourceDescriptor, ImageResourceProvider(), ["img", "image"])
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
5. **Type Safety**: Provide type-safe descriptor classes for pack-specific resources
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

### 10.1 SVG String Transformations

**Important**: Transformations are optional SVG string modifications that change the SVG content itself before returning it. They are NOT rendering instructions. The library returns modified SVG strings; how those strings are rendered is the responsibility of the consuming application.

Supported transformation types (all modify the SVG string content):

- **Tinting**: Replace `currentColor` or specific colors in the SVG string
  - Example: `stroke="currentColor"` → `stroke="#FF0000"`
- **Stroke Width**: Modify `stroke-width` attribute in the SVG string
  - Example: `stroke-width="2"` → `stroke-width="3"`
- **Other SVG attribute modifications**: As needed (rotation via transform attribute, opacity, etc.)

**Universal Pattern**: All icon packs (Lucide, Feather, Material Design, etc.) follow the same pattern:
1. **Discovery**: Find the SVG resource (via function call, file lookup, etc.)
2. **Optional transformations**: Apply SVG string modifications if requested (tint, stroke-width, etc.)
3. **Return**: SVG string content
4. **No custom renderer needed**: Rasterization (SVG → PNG/Image) is handled by consuming applications

Transformations are optional - some packs may support them, others may not. The library provides a mechanism for transformations but does not mandate their implementation.

### 10.2 SVG Optimization (Optional)

Some resource packs may choose to optimize SVG content:

- Remove unnecessary attributes
- Minimize path data
- Remove metadata and comments
- Optimize viewBox

This is an implementation detail of individual resource packs, not a requirement of the discovery library.

### 10.3 Resource Usage (Out of Scope)

**Note**: This library focuses on discovery and retrieval of resources. How those resources are used (rendered, cached, transformed) is the responsibility of the consuming application.

The library returns raw resource content:
- **SVG icons**: SVG strings that can be used by any SVG-capable renderer
- **Raster images**: Image bytes in their native format
- **Other resources**: Raw content in their native format

Consuming applications may:
- Render SVG to raster formats using libraries like CairoSVG, Pillow, or custom renderers
- Cache resources for performance
- Apply additional transformations beyond what the library provides
- Integrate resources into their own rendering pipelines

These concerns are outside the scope of the discovery library.

## 11. Raster Image Resources

### 11.1 Image Resource Descriptors

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class ImageResourceDescriptor:
    """Descriptor for raster image resources."""
    
    pack: str
    name: str
    format: str = "png"  # "png", "jpg", "webp", etc.
    target_size: tuple[int, int] | None = None  # Optional hint for transformations
    resize_mode: str = "fit"  # "fit", "crop", "stretch" (hint for transformations)
```

### 11.2 Image Provider

```python
class ImageResourceProvider(ResourceProvider):
    """Provider for raster image resources."""
    
    def __init__(self, base_path: Path):
        self.base_path = base_path
    
    def get_resource(self, descriptor: object) -> bytes:
        """Get image bytes."""
        if not isinstance(descriptor, ImageResourceDescriptor):
            raise ValueError(f"Expected ImageResourceDescriptor, got {type(descriptor)}")
        
        image_path = self.base_path / f"{descriptor.name}.{descriptor.format}"
        
        if not image_path.exists():
            raise ValueError(f"Image not found: {image_path}")
        
        # Note: Image transformations (resizing, etc.) are optional and implementation-dependent
        # The library returns raw image bytes. Transformations are hints that consuming
        # applications may use, but the library itself doesn't perform transformations.
        
        # Return original image bytes
        with open(image_path, "rb") as f:
            return f.read()
```

## 12. Future Considerations

### 12.1 Audio Resources

Support for audio files:

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class AudioResourceDescriptor:
    """Descriptor for audio resources."""
    
    pack: str
    name: str
    format: str = "mp3"  # "mp3", "ogg", "wav"
    start_time: float | None = None  # Optional hint for transformations
    duration: float | None = None  # Optional hint for transformations
```

### 12.2 Video Resources

Support for video files:

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class VideoResourceDescriptor:
    """Descriptor for video resources."""
    
    pack: str
    name: str
    format: str = "mp4"  # "mp4", "webm"
    target_size: tuple[int, int] | None = None  # Optional hint for transformations
    start_time: float | None = None  # Optional hint for transformations
    duration: float | None = None  # Optional hint for transformations
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

## 13. Design Origins

This design was informed by practical implementations that demonstrated the viability of combining resource discovery with extensible resource pack discovery via EntryPoints. The architecture emphasizes:

- **Independence**: Standalone library with no framework dependencies
- **Extensibility**: EntryPoints mechanism for third-party resource packs
- **Universal Pattern**: All resource packs (Lucide, Feather, Material Design, etc.) follow the same discovery pattern:
  - Discovery: Find the resource (via function call, file lookup, etc.)
  - Optional transformations: Apply resource content modifications if requested (e.g., SVG string transformations)
  - Return: Raw resource content (SVG strings, image bytes, etc.)
  - No custom renderer needed: Rasterization and rendering are handled by consuming applications
- **Clear Boundaries**: Library returns raw content; consuming applications handle rendering, caching, etc.

## 14. Example Usage

### 14.1 Basic Icon Usage

```python
from resourcediscovery import ResourceRegistry, get_default_registry
from resourcediscovery.descriptors import SvgIconDescriptor

# Get default registry
registry = get_default_registry()

# Create icon descriptor with prefix
icon_descriptor = SvgIconDescriptor(
    ref="lucide:lightbulb",
    w=24,  # Hint for transformations, not rendering instruction
    h=24,  # Hint for transformations, not rendering instruction
    tint="#FF0000",  # Optional SVG string transformation hint
)

# Get SVG content (raw SVG string)
svg_content = registry.get_resource(icon_descriptor)
print(svg_content)  # SVG string - how it's used is up to the consuming application
```

### 14.2 Pack-Specific Icon Usage

```python
from resourcediscovery.descriptors import LucideIconDescriptor
from resourcediscovery.providers import LucideProvider

# Create pack-specific descriptor
icon_descriptor = LucideIconDescriptor(
    name="lightbulb",
    w=24,  # Hint for transformations
    h=24,  # Hint for transformations
    tint="#FF0000",  # Optional SVG string transformation hint
    stroke_width=2.0,  # Optional SVG string transformation hint
)

# Get provider and retrieve SVG
registry = get_default_registry()
provider = registry.get_provider(icon_descriptor)
svg_content = provider.get_resource(icon_descriptor)
# svg_content is a raw SVG string - rendering is handled by consuming application
```

### 14.3 Image Resource Usage

```python
from resourcediscovery.descriptors import ImageResourceDescriptor

# Create image descriptor
image_descriptor = ImageResourceDescriptor(
    pack="my-images",
    name="logo",
    format="png",
    target_size=(200, 200),  # Optional hint for transformations
    resize_mode="fit",  # Optional hint for transformations
)

# Get image bytes (raw image data)
registry = get_default_registry()
image_bytes = registry.get_resource(image_descriptor)
# image_bytes is raw image data - how it's used is up to the consuming application
```

### 14.4 Resource Pack Implementation

```python
# my_icon_pack/__init__.py
from my_icon_pack.provider import MyIconProvider
from my_icon_pack.descriptors import MyIconDescriptor

def get_resource_provider():
    """Entry point factory for icon pack."""
    return (MyIconDescriptor, MyIconProvider(), ["myicons", "mi"])

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

