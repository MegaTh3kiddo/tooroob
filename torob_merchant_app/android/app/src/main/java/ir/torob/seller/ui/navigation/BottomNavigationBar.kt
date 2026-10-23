package ir.torob.seller.ui.navigation

import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.BarChart
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.QuestionAnswer
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Storefront
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import androidx.navigation.compose.currentBackStackEntryAsState
import ir.torob.seller.ui.theme.*
import ir.torob.seller.util.PersianFormatters

data class NavItem(
    val route: String,
    val title: String,
    val icon: ImageVector
)

@Composable
fun BottomNavigationBar(
    navController: NavController,
    inquiryBadgeCount: Int = 0
) {
    val items = listOf(
        NavItem(Screen.Inquiries.route, "استعلام‌ها", Icons.Default.QuestionAnswer),
        NavItem(Screen.History.route, "تاریخچه", Icons.Default.History),
        NavItem(Screen.Metrics.route, "عملکرد", Icons.Default.BarChart),
        NavItem(Screen.StoreProfile.route, "فروشگاه", Icons.Default.Storefront),
        NavItem(Screen.Settings.route, "تنظیمات", Icons.Default.Settings)
    )

    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route

    // Don't show bottom bar on auth screens or inquiry detail screen
    if (currentRoute == Screen.Login.route ||
        currentRoute?.startsWith("otp_verify") == true ||
        currentRoute?.startsWith("inquiry_detail") == true
    ) {
        return
    }

    NavigationBar(
        containerColor = MaterialTheme.colorScheme.surface,
        tonalElevation = 8.dp
    ) {
        items.forEach { item ->
            val selected = currentRoute == item.route
            val isInbox = item.route == Screen.Inquiries.route

            NavigationBarItem(
                selected = selected,
                onClick = {
                    if (currentRoute != item.route) {
                        navController.navigate(item.route) {
                            popUpTo(Screen.Inquiries.route) { saveState = true }
                            launchSingleTop = true
                            restoreState = true
                        }
                    }
                },
                icon = {
                    if (isInbox && inquiryBadgeCount > 0) {
                        BadgedBox(
                            badge = {
                                Badge(
                                    containerColor = TorobRed,
                                    contentColor = PureWhite
                                ) {
                                    Text(
                                        text = PersianFormatters.toPersianDigits(inquiryBadgeCount),
                                        fontSize = 10.sp,
                                        fontWeight = FontWeight.Bold
                                    )
                                }
                            }
                        ) {
                            Icon(
                                imageVector = item.icon,
                                contentDescription = item.title,
                                modifier = Modifier.size(20.dp)
                            )
                        }
                    } else {
                        Icon(
                            imageVector = item.icon,
                            contentDescription = item.title,
                            modifier = Modifier.size(20.dp)
                        )
                    }
                },
                label = {
                    Text(
                        text = item.title,
                        fontSize = 10.sp,
                        fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium
                    )
                },
                colors = NavigationBarItemDefaults.colors(
                    selectedIconColor = TorobRed,
                    selectedTextColor = TorobRed,
                    indicatorColor = MaterialTheme.colorScheme.primaryContainer,
                    unselectedIconColor = MaterialTheme.colorScheme.onSurfaceVariant,
                    unselectedTextColor = MaterialTheme.colorScheme.onSurfaceVariant
                )
            )
        }
    }
}
