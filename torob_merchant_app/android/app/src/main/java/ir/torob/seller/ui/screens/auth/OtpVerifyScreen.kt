package ir.torob.seller.ui.screens.auth

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ir.torob.seller.ui.theme.*
import ir.torob.seller.ui.viewmodel.AuthViewModel

@Composable
fun OtpVerifyScreen(
    phone: String,
    viewModel: AuthViewModel,
    onLoginSuccess: () -> Unit,
    onBack: () -> Unit
) {
    val state by viewModel.uiState.collectAsState()

    LaunchedEffect(state.isLoggedIn) {
        if (state.isLoggedIn) {
            onLoginSuccess()
        }
    }

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = Slate50
    ) {
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(24.dp),
            contentAlignment = Alignment.Center
        ) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(24.dp),
                colors = CardDefaults.cardColors(containerColor = PureWhite),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Text(
                        text = "تایید شماره تلفن فروشگاه",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        color = Slate900
                    )

                    Spacer(modifier = Modifier.height(6.dp))

                    Text(
                        text = "کد ۵ رقمی ارسال‌شده به شماره $phone را وارد کنید.",
                        fontSize = 12.sp,
                        color = Slate500,
                        textAlign = TextAlign.Center
                    )

                    if (state.demoOtp != null) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = "کد تایید: ${state.demoOtp}",
                            fontSize = 13.sp,
                            color = TorobGreen,
                            fontWeight = FontWeight.Bold
                        )
                    }

                    Spacer(modifier = Modifier.height(24.dp))

                    OutlinedTextField(
                        value = state.otpCode,
                        onValueChange = viewModel::onOtpChanged,
                        label = { Text("کد تایید ۵ رقمی") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        shape = RoundedCornerShape(12.dp)
                    )

                    if (state.errorMessage != null) {
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = state.errorMessage!!,
                            color = TorobRed,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Medium
                        )
                    }

                    Spacer(modifier = Modifier.height(24.dp))

                    Button(
                        onClick = viewModel::verifyOtp,
                        enabled = !state.isLoading,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(50.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = TorobRed),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        if (state.isLoading) {
                            CircularProgressIndicator(color = PureWhite, modifier = Modifier.size(20.dp))
                        } else {
                            Text(
                                text = "تایید و ورود به برنامه",
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Bold,
                                color = PureWhite
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    TextButton(onClick = onBack) {
                        Text(
                            text = "ویرایش شماره تلفن",
                            fontSize = 12.sp,
                            color = Slate700
                        )
                    }
                }
            }
        }
    }
}
