package ir.torob.seller.ui.navigation

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import androidx.navigation.navDeepLink
import ir.torob.seller.ui.screens.auth.LoginScreen
import ir.torob.seller.ui.screens.auth.OtpVerifyScreen
import ir.torob.seller.ui.screens.history.ResponseHistoryScreen
import ir.torob.seller.ui.screens.inquiries.InquiriesListScreen
import ir.torob.seller.ui.screens.inquiry_detail.InquiryDetailScreen
import ir.torob.seller.ui.screens.metrics.MetricsScreen
import ir.torob.seller.ui.screens.settings.SettingsScreen
import ir.torob.seller.ui.screens.store.StoreProfileScreen
import ir.torob.seller.ui.viewmodel.*

@Composable
fun AppNavGraph(
    navController: NavHostController,
    authViewModel: AuthViewModel,
    inquiryViewModel: InquiryViewModel,
    storeViewModel: StoreViewModel,
    metricsViewModel: MetricsViewModel,
    settingsViewModel: SettingsViewModel,
    isOnline: Boolean,
    hasNotificationPermission: Boolean,
    onRequestNotificationPermission: () -> Unit,
    deepLinkInquiryId: String? = null,
    onDeepLinkHandled: () -> Unit = {}
) {
    val authState by authViewModel.uiState.collectAsState()
    val isLoggedIn = authState.isLoggedIn

    // Deep link redirection if opened via push notification or incoming call answer
    LaunchedEffect(deepLinkInquiryId, isLoggedIn) {
        android.util.Log.d("NavGraphNav", "LaunchedEffect: deepLinkInquiryId=$deepLinkInquiryId, isLoggedIn=$isLoggedIn")
        if (!deepLinkInquiryId.isNullOrBlank() && isLoggedIn) {
            val route = Screen.InquiryDetail.createRoute(deepLinkInquiryId)
            android.util.Log.d("NavGraphNav", "Navigating to: $route")
            navController.navigate(route) {
                launchSingleTop = true
            }
            onDeepLinkHandled()
        }
    }

    val activeInquiries by inquiryViewModel.activeInquiries.collectAsState()

    Scaffold(
        bottomBar = {
            BottomNavigationBar(
                navController = navController,
                inquiryBadgeCount = activeInquiries.size
            )
        }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = if (isLoggedIn) Screen.Inquiries.route else Screen.Login.route,
            modifier = Modifier.padding(innerPadding)
        ) {
            composable(Screen.Login.route) {
                LoginScreen(
                    viewModel = authViewModel,
                    onNavigateToOtp = { phone ->
                        navController.navigate(Screen.OtpVerify.createRoute(phone))
                    },
                    onLoginSuccess = {
                        navController.navigate(Screen.Inquiries.route) {
                            popUpTo(Screen.Login.route) { inclusive = true }
                        }
                    }
                )
            }

            composable(
                route = Screen.OtpVerify.route,
                arguments = listOf(navArgument("phone") { type = NavType.StringType })
            ) { backStackEntry ->
                val phone = backStackEntry.arguments?.getString("phone") ?: ""
                OtpVerifyScreen(
                    phone = phone,
                    viewModel = authViewModel,
                    onLoginSuccess = {
                        navController.navigate(Screen.Inquiries.route) {
                            popUpTo(Screen.Login.route) { inclusive = true }
                        }
                    },
                    onBack = { navController.popBackStack() }
                )
            }

            composable(Screen.Inquiries.route) {
                InquiriesListScreen(
                    viewModel = inquiryViewModel,
                    isOnline = isOnline,
                    hasNotificationPermission = hasNotificationPermission,
                    onRequestNotificationPermission = onRequestNotificationPermission,
                    onInquiryClick = { inqId ->
                        navController.navigate(Screen.InquiryDetail.createRoute(inqId))
                    },
                    onNavigateToHistory = {
                        navController.navigate(Screen.History.route) {
                            popUpTo(Screen.Inquiries.route) { saveState = true }
                            launchSingleTop = true
                            restoreState = true
                        }
                    }
                )
            }

            composable(
                route = Screen.InquiryDetail.route,
                arguments = listOf(navArgument("inquiryId") { type = NavType.StringType }),
                deepLinks = listOf(navDeepLink { uriPattern = "torob://inquiry/{inquiryId}" })
            ) { backStackEntry ->
                val inqId = backStackEntry.arguments?.getString("inquiryId") ?: ""
                InquiryDetailScreen(
                    inquiryId = inqId,
                    viewModel = inquiryViewModel,
                    isOnline = isOnline,
                    onBack = { navController.popBackStack() }
                )
            }

            composable(Screen.History.route) {
                ResponseHistoryScreen(
                    viewModel = inquiryViewModel,
                    isOnline = isOnline,
                    onInquiryClick = { inqId ->
                        navController.navigate(Screen.InquiryDetail.createRoute(inqId))
                    }
                )
            }

            composable(Screen.StoreProfile.route) {
                StoreProfileScreen(viewModel = storeViewModel)
            }

            composable(Screen.Metrics.route) {
                MetricsScreen(viewModel = metricsViewModel)
            }

            composable(Screen.Settings.route) {
                SettingsScreen(
                    settingsViewModel = settingsViewModel,
                    authViewModel = authViewModel,
                    hasNotificationPermission = hasNotificationPermission,
                    onRequestNotificationPermission = onRequestNotificationPermission,
                    onLogout = {
                        navController.navigate(Screen.Login.route) {
                            popUpTo(0) { inclusive = true }
                        }
                    }
                )
            }
        }
    }
}
