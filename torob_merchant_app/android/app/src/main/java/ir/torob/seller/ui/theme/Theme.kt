package ir.torob.seller.ui.theme

import android.app.Activity
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.unit.LayoutDirection
import androidx.core.view.WindowCompat

private val TorobLightColorScheme = lightColorScheme(
    primary = TorobRed,
    onPrimary = Color.White,
    primaryContainer = TorobRedLight,
    onPrimaryContainer = TorobRedDark,
    secondary = TorobSuccess,
    onSecondary = Color.White,
    secondaryContainer = TorobSuccessLight,
    onSecondaryContainer = Color(0xFF1B5E20),
    background = TorobBackground,
    onBackground = TorobTextPrimary,
    surface = TorobSurface,
    onSurface = TorobTextPrimary,
    surfaceVariant = SurfaceVariantLight,
    onSurfaceVariant = TorobTextSecondary,
    outline = TorobDivider,
    error = TorobError,
    onError = Color.White,
    errorContainer = TorobErrorLight,
    onErrorContainer = TorobRedDark
)

private val TorobDarkColorScheme = darkColorScheme(
    primary = Color(0xFFEF5350),
    onPrimary = Color.White,
    primaryContainer = Color(0xFF5F1412),
    onPrimaryContainer = Color(0xFFFFCDD2),
    secondary = Color(0xFF66BB6A),
    onSecondary = Color.Black,
    secondaryContainer = Color(0xFF1E3A20),
    onSecondaryContainer = Color(0xFFC8E6C9),
    background = Color(0xFF121212),
    onBackground = Color(0xFFE0E0E0),
    surface = Color(0xFF1E1E1E),
    onSurface = Color(0xFFE0E0E0),
    surfaceVariant = Color(0xFF2C2C2C),
    onSurfaceVariant = Color(0xFFA0A0A0),
    outline = Color(0xFF383838),
    error = Color(0xFFEF5350),
    onError = Color.Black,
    errorContainer = Color(0xFF5F1412),
    onErrorContainer = Color(0xFFFFCDD2)
)

@Composable
fun TorobSellerTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = if (darkTheme) TorobDarkColorScheme else TorobLightColorScheme
    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = (if (darkTheme) Color(0xFF1E1E1E) else TorobSurface).toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = !darkTheme
        }
    }

    // Enforce Right-to-Left (RTL) LayoutDirection and Vazir typography for Persian UI
    CompositionLocalProvider(
        LocalLayoutDirection provides LayoutDirection.Rtl,
        androidx.compose.material3.LocalTextStyle provides androidx.compose.ui.text.TextStyle(fontFamily = VazirFontFamily)
    ) {
        MaterialTheme(
            colorScheme = colorScheme,
            typography = Typography,
            content = content
        )
    }
}
