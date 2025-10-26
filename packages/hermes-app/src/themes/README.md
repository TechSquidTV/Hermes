# Hermes Theme System

This directory contains the theme files for the Hermes application. Each theme defines color schemes for both dark and light modes.

## Available Themes

- **Hermes** (default) - Warm orange accents with black and white base
- **Nord** - Arctic-inspired cool blues and greens
- **Dracula** - Vibrant purples and cyans
- **Tokyo Night** - Deep purples and blues inspired by Tokyo at night
- **Catppuccin** - Pastel colors with smooth gradients

## Adding a Custom Theme

### Step 1: Create Your Theme File

1. Copy `_template.css` to a new file (e.g., `my-theme.css`)
2. Replace all instances of `theme-custom` with your theme name (e.g., `theme-mytheme`)
3. Update the color values using HSL format

### Step 2: Color Format

All colors use HSL values without the `hsl()` wrapper:

```css
/* Format: hue saturation lightness */
--primary: 210 50% 50%;

/* This is equivalent to: */
/* hsl(210, 50%, 50%) */
```

**HSL Components:**
- **Hue** (0-360): The color on the color wheel
  - 0/360 = Red
  - 120 = Green
  - 240 = Blue
- **Saturation** (0-100%): Color intensity
  - 0% = Gray
  - 100% = Full color
- **Lightness** (0-100%): Brightness
  - 0% = Black
  - 50% = Normal
  - 100% = White

### Step 3: Required CSS Variables

Every theme **must** define these variables for both `.theme-name` (dark) and `.theme-name.light` (light):

#### Base Colors
- `--background` - Main background
- `--foreground` - Main text color

#### Card/Panel Colors  
- `--card` - Card background
- `--card-foreground` - Card text

#### Popover Colors
- `--popover` - Popover background
- `--popover-foreground` - Popover text

#### Action Colors
- `--primary` - Primary buttons/links
- `--primary-foreground` - Text on primary

#### Secondary Colors
- `--secondary` - Secondary elements
- `--secondary-foreground` - Text on secondary

#### Muted Colors
- `--muted` - Muted backgrounds
- `--muted-foreground` - Muted text

#### Accent Colors
- `--accent` - Accent color
- `--accent-foreground` - Text on accent

#### Destructive Colors
- `--destructive` - Error/delete actions
- `--destructive-foreground` - Text on destructive

#### Form Colors
- `--border` - Border color
- `--input` - Input border
- `--ring` - Focus ring

#### Sidebar Colors (All required)
- `--sidebar-background`
- `--sidebar-foreground`
- `--sidebar-primary`
- `--sidebar-primary-foreground`
- `--sidebar-accent`
- `--sidebar-accent-foreground`
- `--sidebar-border`
- `--sidebar-ring`
- `--sidebar`

#### Grain Effect (Optional)
- `--grain-opacity` - Opacity of the grain texture (0 to disable, 0.01-0.10 recommended)
- `--grain-blend-mode` - CSS blend mode (overlay, soft-light, multiply, screen, etc.)
- `--grain-visibility` - Show/hide grain (visible or hidden)

**Grain Effect Examples:**
```css
/* Subtle grain for clean themes */
--grain-opacity: 0.03;
--grain-blend-mode: soft-light;
--grain-visibility: visible;

/* Dramatic grain for vintage themes */
--grain-opacity: 0.08;
--grain-blend-mode: multiply;
--grain-visibility: visible;

/* Disable grain completely */
--grain-opacity: 0;
--grain-blend-mode: overlay;
--grain-visibility: hidden;
```


### Step 4: Register Your Theme

Add your theme import to `src/style.css`:

```css
@import "./themes/my-theme.css";
```

### Step 5: Add Theme Metadata

Update `src/themes/index.ts` to include your theme:

```typescript
{
  id: 'mytheme',
  name: 'My Custom Theme',
  description: 'A beautiful custom theme',
  author: 'Your Name',
  preview: {
    primary: 'hsl(210, 50%, 50%)',
    background: 'hsl(0, 0%, 10%)',
    accent: 'hsl(180, 50%, 50%)',
  },
}
```

### Step 6: Test Your Theme

1. Restart the development server
2. Go to Settings → Appearance
3. Select your new theme from the dropdown
4. Test both light and dark modes

## Tips for Creating Themes

### Color Harmony

- **Monochromatic**: Use one hue with varying saturation/lightness
- **Analogous**: Use adjacent hues on the color wheel (e.g., 30° apart)
- **Complementary**: Use opposite hues (e.g., 180° apart)
- **Triadic**: Use three hues equally spaced (120° apart)

### Accessibility

- Ensure sufficient contrast between foreground and background (4.5:1 minimum)
- Test with color blindness simulators
- Use tools like WebAIM Contrast Checker

### Consistency

- Keep similar saturation levels across colors
- Use consistent lightness steps between variants
- Maintain visual hierarchy with lightness values

## Resources

- [HSL Color Picker](https://hslpicker.com/)
- [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)
- [Color Wheel](https://www.sessions.edu/color-calculator/)
- [Coolors Palette Generator](https://coolors.co/)

## Troubleshooting

**Theme not showing up?**
- Check that you added the `@import` to `style.css`
- Check that you added metadata to `themes/index.ts`
- Restart the development server

**Colors look wrong?**
- Verify HSL values are in the correct format (no `hsl()` wrapper)
- Check that all required variables are defined
- Test both dark and light mode classes

**Light mode not working?**
- Ensure you have `.theme-name.light` class defined
- Check that all color variables are redefined for light mode

