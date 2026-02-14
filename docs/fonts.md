# Font Discovery Architecture

## 1. Overview

This document describes the architecture and design for a standalone font discovery system that combines platform-specific system font detection with extensible font pack discovery via Python EntryPoints.

### 1.1 Purpose

The font discovery system provides a unified interface for locating and resolving fonts across two sources:

1. **System Fonts**: Platform-specific system font directories (macOS, Linux, Windows)
2. **Font Packs**: Font packages discovered via Python EntryPoints (supports both first-party application fonts and third-party font packages)

### 1.2 Core Value Proposition

- **Cross-platform**: Unified API across macOS, Linux, and Windows
- **Extensible**: Font packs can be added via standard Python EntryPoints mechanism
- **Efficient**: Lazy discovery with in-memory caching
- **Flexible**: Supports font matching by family, weight, and style with intelligent fallback

### 1.3 Influences & Similar Systems

- **fontlib** (Python): Demonstrates multi-source font management with EntryPoints
- **system-fonts** (Rust): Reference implementation for locale-aware, platform-specific font discovery
- **font-kit** (Rust): Cross-platform font library interface with system font enumeration
- **Fontsource**: NPM-based self-hosted font packages with version locking

## 2. Architecture Overview

The font discovery system follows a two-tier discovery model:

```
┌─────────────────────────────────────────────────────────┐
│                    Font Registry                        │
│  (Unified interface for font lookup and resolution)     │
└─────────────────────────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐
│ System Fonts │ │ Font Packs   │
│  Discovery   │ │  Discovery   │
└──────────────┘ └──────────────┘
        │               │
        ▼               ▼
┌──────────────┐ ┌──────────────┐
│ Platform-    │ │ EntryPoints  │
│ specific     │ │ mechanism    │
│ paths        │ │              │
└──────────────┘ └──────────────┘
```

### 2.1 Discovery Order

Fonts are discovered in the following priority order:

1. **Font Packs** (Highest Priority): Explicitly registered fonts (first-party or dependencies) via EntryPoints
2. **System Fonts** (Lowest Priority): Fallback to locally installed fonts in platform-specific directories

*Rationale: Ensures application consistency (branding/layout) regardless of the user's local environment. Font Packs represent bundled/application intent - if a developer explicitly adds a font pack, they want that specific version of the font. System fonts serve as the fallback.*

## 3. System Font Discovery

System font discovery is platform-specific, requiring different directory paths for each operating system.

### 3.1 Platform-Specific Directories

#### macOS

```python
[
    Path("/System/Library/Fonts"),      # System fonts
    Path("/Library/Fonts"),              # System-wide fonts
    Path.home() / "Library" / "Fonts",  # User fonts
]
```

#### Linux

```python
[
    Path.home() / ".fonts",                          # Legacy user fonts
    Path("/usr/share/fonts"),                        # System fonts
    Path("/usr/local/share/fonts"),                 # Local system fonts
    Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "fonts",  # User fonts (XDG Base Directory)
    Path("/run/host/fonts"),                         # Flatpak/Snap sandbox fonts
]
```

#### Windows

```python
[
    Path(os.environ.get("WINDIR", "C:\\Windows")) / "Fonts",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Fonts",
]
```

### 3.2 Font File Discovery

Font files are discovered by recursively scanning directories for common font file extensions:

- `.ttf` - TrueType Font
- `.otf` - OpenType Font
- `.ttc` - TrueType Collection
- `.woff` - Web Open Font Format
- `.woff2` - Web Open Font Format 2.0

**Note**: While `.woff` and `.woff2` are web font formats, they may appear in system directories and should be supported for completeness.

### 3.3 Implementation Considerations

- **Permission Handling**: Gracefully handle directories that cannot be read (OSError, PermissionError)
- **Symlink Resolution**: Follow symlinks to discover fonts in linked directories
- **Performance**: Use lazy discovery - only scan directories when `discover()` is called
- **Caching**: Cache discovered fonts in memory to avoid repeated filesystem scans

## 4. Font Pack Discovery

Font packs are font packages discovered via Python EntryPoints. This mechanism supports both:

- **First-party fonts**: Application's own fonts registered via EntryPoint in the application's `pyproject.toml`
- **Third-party fonts**: Separate font packages installed as dependencies

Both use the same EntryPoints mechanism, providing a unified approach for all non-system fonts.

### 4.1 EntryPoints Mechanism

Font packs register themselves using the EntryPoints mechanism defined in PEP 621 and implemented by `importlib.metadata` (Python 3.8+) or `importlib_metadata` (backport).

**Entry Point Group**: `fontpacks` (or project-specific like `myproject.fontpacks`)

**Entry Point Format**: Factory function that returns font directory paths

### 4.2 Font Pack Structure

A font pack (whether first-party or third-party) should define an entry point in its `setup.py` or `pyproject.toml`:

**setup.py**:
```python
setup(
    name="my-font-pack",
    entry_points={
        "fontpacks": [
            "my-font-pack = my_font_pack:get_font_directories",
        ],
    },
)
```

**pyproject.toml**:
```toml
[project.entry-points."fontpacks"]
"my-font-pack" = "my_font_pack:get_font_directories"
```

### 4.3 Font Pack Implementation

The entry point factory function returns font directory paths. This works the same way for both first-party and third-party font packs:

**Example: First-party font pack (application's own fonts)**

```python
# myapp/__init__.py or myapp/fonts.py
from pathlib import Path
from importlib.resources import files

def get_font_directories():
    """Entry point factory for application's bundled fonts."""
    package = files("myapp.fonts")
    return [Path(str(package))]
```

**Example: Third-party font pack (separate package)**

```python
# my_font_pack/__init__.py
from pathlib import Path
from importlib.resources import files

def get_font_directories():
    """Entry point factory returning font directory paths."""
    # Option 1: Return Path objects
    package = files("my_font_pack.fonts")
    return [Path(str(package))]
    
    # Option 2: Return string paths
    # return [str(Path(__file__).parent / "fonts")]
    
    # Option 3: Return multiple directories
    # return [
    #     Path(str(files("my_font_pack.fonts"))),
    #     Path.home() / ".my_font_pack" / "fonts",
    # ]
```

**Example: Application registering its own fonts in pyproject.toml**

```toml
[project.entry-points."fontpacks"]
"myapp-fonts" = "myapp:get_font_directories"
```

```python
# my_font_pack/__init__.py
from pathlib import Path
from importlib.resources import files

def get_font_directories():
    """Entry point factory returning font directory paths."""
    # Option 1: Return Path objects
    package = files("my_font_pack.fonts")
    return [Path(str(package))]
    
    # Option 2: Return string paths
    # return [str(Path(__file__).parent / "fonts")]
    
    # Option 3: Return multiple directories
    # return [
    #     Path(str(files("my_font_pack.fonts"))),
    #     Path.home() / ".my_font_pack" / "fonts",
    # ]
```

### 4.4 Discovery Implementation

```python
def get_font_pack_directories() -> list[Path]:
    """Get font pack directories from entry points."""
    dirs: list[Path] = []
    
    try:
        from importlib.metadata import entry_points
        eps = entry_points(group="fontpacks")
    except ImportError:
        # Python < 3.10 fallback
        try:
            import importlib_metadata
            eps = importlib_metadata.entry_points(group="fontpacks")
        except ImportError:
            return dirs
    
    for ep in eps:
        try:
            factory = ep.load()
            result = factory()
            
            # Handle various return types
            if isinstance(result, (list, tuple)):
                for item in result:
                    path = Path(item) if isinstance(item, str) else item
                    if path.exists():
                        dirs.append(path)
            elif isinstance(result, (str, Path)):
                path = Path(result) if isinstance(result, str) else result
                if path.exists():
                    dirs.append(path)
        except Exception:
            # Skip invalid entry points
            continue
    
    return dirs
```

## 5. Font Metadata Parsing

Font metadata (family name, weight, style) must be extracted from font files to enable intelligent matching.

### 5.1 Font Parsing Libraries

**Required**: `fonttools`
- Comprehensive font metadata extraction
- Supports TTF, OTF, TTC, WOFF, WOFF2
- Access to OpenType tables (name, OS/2, head)
- **Critical**: Parsing binary font tables is the only reliable way to get family names. Filename heuristics fail ~30% of the time (e.g., "Arial Narrow" is a family, not just "Arial" with a weight).

**Note**: If fonttools is unavailable, the implementation should log a warning and skip the file rather than guessing. Guessing leads to "ghost bugs" where fonts appear with wrong weights or family names.

### 5.2 FontInfo Data Structure

```python
@dataclass(frozen=True, slots=True)
class FontInfo:
    """Information about a discovered font."""
    
    path: Path                    # Path to font file
    family: str                   # Font family name
    weight: int | None = None     # Font weight (100-900, None if unknown)
    style: str = "normal"         # "normal" or "italic"
    width: str | None = None      # Font width/stretch (e.g., "normal", "condensed", "expanded", None if unknown)
    postscript_name: str | None = None  # PostScript name (e.g., "Roboto-BoldItalic") for native OS APIs
    variant: str | None = None    # e.g., "Regular", "Bold", "Italic", "Bold Italic"
```

### 5.3 Metadata Extraction

#### Using fonttools (Required)

```python
from fonttools.ttLib import TTFont

def parse_font_file(path: Path) -> FontInfo | None:
    """Parse font file using fonttools."""
    try:
        font = TTFont(str(path))
        
        # Extract family name from name table
        name_table = font.get("name")
        family = name_table.getDebugName(1)  # Family name
        
        # Extract PostScript name (name ID 6)
        postscript_name = name_table.getDebugName(6)
        
        # Extract weight from OS/2 table
        os2 = font.get("OS/2")
        weight = os2.usWeightClass if os2 else None
        
        # Extract style from name table or OS/2
        style = "normal"
        if os2 and os2.fsSelection & 0x01:  # Italic bit
            style = "italic"
        
        # Extract width/stretch from OS/2 table
        width = None
        if os2:
            # Map OS/2 usWidthClass to CSS width values
            width_map = {
                1: "ultra-condensed", 2: "extra-condensed", 3: "condensed",
                4: "semi-condensed", 5: "normal", 6: "semi-expanded",
                7: "expanded", 8: "extra-expanded", 9: "ultra-expanded"
            }
            width = width_map.get(os2.usWidthClass, "normal")
        
        return FontInfo(
            path=path,
            family=family,
            weight=weight,
            style=style,
            width=width,
            postscript_name=postscript_name,
        )
    except Exception:
        return None
```

### 5.4 Filename-Based Heuristics (Experimental/Unreliable)

**Warning**: Filename-based parsing is unreliable and should only be used as a last resort when fonttools is unavailable. This method fails ~30% of the time and cannot distinguish between font families and width variants (e.g., "Arial Narrow" vs "Arial" with condensed width).

When font metadata is unavailable, parse weight and style from filename:

```python
def parse_filename(path: Path) -> tuple[int | None, str]:
    """Parse weight and style from filename."""
    stem = path.stem.lower()
    weight: int | None = None
    style = "normal"
    
    # Weight mapping
    weight_map = {
        "thin": 100, "extralight": 200, "light": 300,
        "regular": 400, "normal": 400, "medium": 500,
        "semibold": 600, "bold": 700, "extrabold": 800, "black": 900,
    }
    
    for keyword, w in weight_map.items():
        if keyword in stem:
            weight = w
            break
    
    # Style detection
    if "italic" in stem or "oblique" in stem:
        style = "italic"
    
    return weight, style
```

## 6. Font Resolution Algorithm

The font resolution algorithm matches font requests (family, size, weight, style) to discovered fonts using a scoring system.

### 6.1 Matching Criteria

1. **Family Name**: Exact match (case-insensitive)
2. **Weight**: Closest match (prefer exact, then closest)
3. **Style**: Exact match (normal vs italic)
4. **Width/Stretch**: Closest match (prefer exact, then closest)

### 6.2 Scoring Algorithm

```python
def find_font(
    self,
    family: str,
    size: int,
    weight: int | None = None,
    style: str = "normal",
    width: str | None = None,
) -> ImageFont.FreeTypeFont | None:
    """Find and load a font by family, size, weight, style, and width."""
    self.discover()
    
    family_lower = family.lower()
    candidates = self._fonts.get(family_lower, [])
    
    if not candidates:
        return None
    
    # Score candidates using CSS-style matching
    best: FontInfo | None = None
    best_score = -1
    
    # Width mapping for scoring
    width_order = ["ultra-condensed", "extra-condensed", "condensed",
                   "semi-condensed", "normal", "semi-expanded",
                   "expanded", "extra-expanded", "ultra-expanded"]
    
    for candidate in candidates:
        score = 0
        
        # Weight matching (closer is better, max 1000 points)
        if weight is not None and candidate.weight is not None:
            weight_diff = abs(candidate.weight - weight)
            score += 1000 - weight_diff  # Prefer closer weights
        elif weight is None or candidate.weight is None:
            score += 500  # Neutral score if weight unspecified
        
        # Style matching (exact match required, 100 points)
        if candidate.style == style:
            score += 100
        
        # Width matching (closer is better, max 500 points)
        if width is not None and candidate.width is not None:
            try:
                req_idx = width_order.index(width)
                cand_idx = width_order.index(candidate.width)
                width_diff = abs(req_idx - cand_idx)
                score += 500 - (width_diff * 50)  # Prefer closer widths
            except ValueError:
                score += 250  # Unknown width values get neutral score
        elif width is None or candidate.width is None:
            score += 250  # Neutral score if width unspecified
        
        if score > best_score:
            best_score = score
            best = candidate
    
    if best is None:
        best = candidates[0]  # Fallback to first candidate
    
    # Load and return font
    try:
        return ImageFont.truetype(str(best.path), size=size)
    except Exception:
        return None
```

### 6.3 Fallback Strategy

If no exact match is found:

1. **Family Fallback**: Return first font in family (if any candidates exist)
2. **System Fallback**: Use platform default font (implementation-dependent)
3. **Error**: Return `None` if no font can be resolved

## 7. Caching Strategy

Font discovery and resolution results are cached to improve performance.

### 7.1 Discovery Cache

- **Font Registry**: Cache discovered `FontInfo` objects keyed by family name (lowercase)
- **Priority Handling**: When multiple fonts with the same family name exist, Font Pack fonts override System Font fonts in the cache
- **Lazy Discovery**: Only discover fonts when `discover()` is called
- **One-time Discovery**: Mark registry as discovered to avoid repeated scans

### 7.2 Resolution Cache

- **Font Instance Cache**: Cache loaded `ImageFont` objects keyed by `(family, size, weight, style, width)`
- **Path Cache**: Cache font file paths for quick lookup
- **Invalidation**: Remove cache entries if font file becomes unavailable

### 7.3 Cache Implementation

```python
class FontRegistry:
    def __init__(self) -> None:
        self._fonts: dict[str, list[FontInfo]] = {}  # family -> [FontInfo]
        self._font_sources: dict[Path, str] = {}  # path -> "fontpack" | "system"
        self._cache: dict[tuple[str, int, int | None, str, str | None], Path] = {}
        self._discovered = False
    
    def discover(self) -> None:
        """Discover fonts with priority: Font Packs first, then System Fonts."""
        if self._discovered:
            return
        
        # Discover Font Packs first (highest priority)
        font_pack_dirs = get_font_pack_directories()
        for dir_path in font_pack_dirs:
            self._scan_directory(dir_path, source="fontpack")
        
        # Discover System Fonts second (fallback)
        system_dirs = get_system_font_directories()
        for dir_path in system_dirs:
            self._scan_directory(dir_path, source="system", allow_override=False)
        
        self._discovered = True
    
    def _scan_directory(self, dir_path: Path, source: str, allow_override: bool = True) -> None:
        """Scan directory and add fonts, respecting priority."""
        for font_file in self._find_font_files(dir_path):
            font_info = parse_font_file(font_file)
            if font_info:
                family_lower = font_info.family.lower()
                
                # If font pack, always add (may override system fonts)
                # If system font, only add if not already present from font pack
                if allow_override or family_lower not in self._fonts:
                    if family_lower not in self._fonts:
                        self._fonts[family_lower] = []
                    self._fonts[family_lower].append(font_info)
                    self._font_sources[font_info.path] = source
```

## 8. API Design

### 8.1 Core Classes

#### FontRegistry

```python
class FontRegistry:
    """Registry for discovering and resolving fonts."""
    
    def discover(self) -> None:
        """Discover fonts from all sources (Font Packs first, then System Fonts)."""
        ...
    
    def find_font(
        self,
        family: str,
        size: int,
        weight: int | None = None,
        style: str = "normal",
        width: str | None = None,
    ) -> ImageFont.FreeTypeFont | None:
        """Find and load a font."""
        ...
    
    def list_families(self) -> Iterator[str]:
        """List all discovered font families."""
        ...
    
    def get_font_path(
        self,
        family: str,
        weight: int | None = None,
        style: str = "normal",
        width: str | None = None,
    ) -> Path | None:
        """Get path to font file."""
        ...
```

#### FontInfo

```python
@dataclass(frozen=True, slots=True)
class FontInfo:
    """Information about a discovered font."""
    path: Path
    family: str
    weight: int | None = None
    style: str = "normal"
    width: str | None = None
    postscript_name: str | None = None
    variant: str | None = None
```

### 8.2 Factory Functions

```python
def get_default_registry() -> FontRegistry:
    """Get the default global font registry instance."""
    ...

def get_system_font_directories() -> list[Path]:
    """Get platform-specific system font directories."""
    ...

def get_font_pack_directories() -> list[Path]:
    """Get font pack directories from entry points."""
    ...
```

### 8.3 Font Reference (Optional)

For applications that need to serialize font references:

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class FontRef:
    """Font reference that resolves via font registry."""
    
    family: str
    size: int
    weight: int | None = None
    style: str = "normal"
    
    def to_image_font(
        self, registry: FontRegistry | None = None
    ) -> ImageFont.FreeTypeFont | None:
        """Resolve this font reference to a PIL ImageFont."""
        ...
```

## 9. Best Practices

### 9.1 Lessons from Existing Solutions

**fontlib**:
- Uses EntryPoints for extensibility
- Supports both API and CLI interfaces
- Demonstrates multi-source font management

**system-fonts** (Rust):
- Locale-aware font selection
- Cached font database for performance
- Best-effort resolution (graceful fallback)

**font-kit**:
- Cross-platform system font enumeration
- Proper font metadata extraction
- Support for variable fonts

### 9.2 Implementation Recommendations

1. **Lazy Discovery**: Only discover fonts when needed
2. **Error Handling**: Gracefully handle missing fonts, permission errors, and invalid font files
3. **Caching**: Cache both discovery results and loaded font instances
4. **Extensibility**: Use EntryPoints for font pack discovery
5. **Platform Abstraction**: Hide platform-specific details behind unified API
6. **Metadata Priority**: Prefer font file metadata over filename heuristics

### 9.3 Performance Considerations

- **One-time Discovery**: Scan filesystem only once per registry instance
- **Lazy Loading**: Load font files only when `find_font()` is called
- **Cache Management**: Use appropriate cache sizes and invalidation strategies
- **Parallel Discovery**: Consider parallel directory scanning for large font collections

## 10. Future Considerations

### 10.1 Locale-Aware Selection

Support locale-based font selection for internationalization:

```python
def find_font_for_locale(
    self,
    family: str,
    locale: str,
    size: int,
    weight: int | None = None,
    style: str = "normal",
) -> ImageFont.FreeTypeFont | None:
    """Find font with locale-aware fallback."""
    # Try exact locale match first
    # Fall back to language family
    # Fall back to default
    ...
```

### 10.2 Font Fallback Chains

Implement CSS-like font fallback chains:

```python
def find_font_with_fallback(
    self,
    families: list[str],  # ["Arial", "Helvetica", "sans-serif"]
    size: int,
    weight: int | None = None,
    style: str = "normal",
) -> ImageFont.FreeTypeFont | None:
    """Find font using fallback chain."""
    for family in families:
        font = self.find_font(family, size, weight, style)
        if font:
            return font
    return None
```

### 10.3 Variable Fonts

Support variable fonts (OpenType Variable Fonts) with custom axis values:

```python
def find_variable_font(
    self,
    family: str,
    size: int,
    weight: int | None = None,
    width: int | None = None,  # Variable axis
    style: str = "normal",
) -> ImageFont.FreeTypeFont | None:
    """Find and configure variable font."""
    ...
```

### 10.4 Font Validation

Add font validation and integrity checks:

```python
def validate_font(self, path: Path) -> bool:
    """Validate font file integrity."""
    # Check file format
    # Verify font tables
    # Check for corruption
    ...
```

## 11. Design Origins

This design was informed by practical implementations that demonstrated the viability of combining system font discovery with extensible font pack discovery via EntryPoints. The architecture emphasizes:

- **Independence**: Standalone library with minimal framework dependencies
- **Extensibility**: EntryPoints mechanism for third-party font packs
- **Cross-platform**: Unified API across macOS, Linux, and Windows
- **Required Dependencies**: fonttools (required for reliable font metadata extraction), PIL/Pillow (required for font loading)

## 12. Example Usage

### 12.1 Basic Usage

```python
from fontdiscovery import FontRegistry, get_default_registry

# Get default registry
registry = get_default_registry()

# Discover fonts (lazy, called automatically on first use)
registry.discover()

# Find a font
font = registry.find_font("Arial", size=16, weight=700, style="normal", width="normal")
if font:
    # Use font with PIL
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (100, 50), "white")
    draw = ImageDraw.Draw(img)
    draw.text((10, 10), "Hello", font=font, fill="black")
```

### 12.2 Custom Registry

```python
from fontdiscovery import FontRegistry

# Create custom registry
registry = FontRegistry()

# Add custom font directory
from pathlib import Path
custom_fonts = Path.home() / "custom_fonts"
# (Would need API extension to add directories)

# Use registry
font = registry.find_font("CustomFont", size=12)
```

### 12.3 Font Pack Implementation

**First-party font pack (application's own fonts):**

```python
# myapp/fonts.py
from pathlib import Path
from importlib.resources import files

def get_font_directories():
    """Entry point factory for application's bundled fonts."""
    package = files("myapp.fonts")
    return [Path(str(package))]

# pyproject.toml
# [project.entry-points."fontpacks"]
# "myapp-fonts" = "myapp.fonts:get_font_directories"
```

**Third-party font pack (separate package):**

```python
# my_font_pack/__init__.py
from pathlib import Path
from importlib.resources import files

def get_font_directories():
    """Entry point factory for font pack."""
    package = files("my_font_pack.fonts")
    return [Path(str(package))]

# pyproject.toml
# [project.entry-points."fontpacks"]
# "my-font-pack" = "my_font_pack:get_font_directories"
```

## 13. Comparison with Existing Solutions

| Feature | This Design | fontlib | system-fonts | font-kit |
|---------|-------------|---------|--------------|----------|
| System Fonts | ✅ | ✅ | ✅ | ✅ |
| Font Packs (EntryPoints) | ✅ | ✅ | ❌ | ❌ |
| Cross-platform | ✅ | ✅ | ✅ | ✅ |
| Locale-aware | 🔄 Future | ❌ | ✅ | ❌ |
| Variable Fonts | 🔄 Future | ❌ | ❌ | ✅ |
| Language | Python | Python | Rust | Rust |

**Key Differentiators**:
- Combines system fonts and pack-based discovery (unified EntryPoints for both first-party and third-party fonts)
- Python-native with EntryPoints extensibility
- Required dependencies: fonttools (font metadata), PIL/Pillow (font loading)
- Font Packs override System Fonts for application consistency
- Designed for standalone project extraction

