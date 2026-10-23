package ir.torob.seller.ui.screens.store

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircleOutline
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.HourglassTop
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material.icons.filled.SupportAgent
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ir.torob.seller.data.model.ShopChangeRequestCreateDto
import ir.torob.seller.data.model.ShopUpdateDto
import ir.torob.seller.ui.theme.*
import ir.torob.seller.ui.viewmodel.StoreViewModel

@Composable
fun StoreProfileScreen(
    viewModel: StoreViewModel
) {
    val state by viewModel.uiState.collectAsState()
    val shop = state.shop

    LaunchedEffect(Unit) {
        viewModel.loadProfile()
    }

    var showRequestDialog by remember { mutableStateOf(false) }
    var reqShopName by remember { mutableStateOf("") }
    var reqPhone by remember { mutableStateOf("") }
    var reqAddress by remember { mutableStateOf("") }
    var reqOpenTime by remember { mutableStateOf("") }
    var reqCloseTime by remember { mutableStateOf("") }
    var reqReason by remember { mutableStateOf("") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
    ) {
        Surface(
            modifier = Modifier.fillMaxWidth(),
            color = MaterialTheme.colorScheme.surface,
            shadowElevation = 1.dp
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "اطلاعات و وضعیت فروشگاه",
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Black,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Text(
                    text = "تنظیم باز/بسته بودن فروشگاه و ساعات کاری",
                    fontSize = 11.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }

        if (state.isLoading && shop == null) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(color = TorobRed)
            }
        } else {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // Store Operating Scenario Selector Card
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .border(1.dp, MaterialTheme.colorScheme.outline, RoundedCornerShape(16.dp)),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
                ) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(
                            text = "وضعیت فعالیت فروشگاه در ترب",
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = "یکی از سناریوهای زیر را برای وضعیت فروشگاه و دریافت استعلام انتخاب کنید:",
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )

                        Spacer(modifier = Modifier.height(14.dp))

                        val currentScenario = when {
                            shop?.isOpen == true && shop.acceptInquiries -> 1
                            shop?.isOpen == true && !shop.acceptInquiries -> 2
                            else -> 3
                        }

                        // Scenario 1: فروشگاه فعال و پشتیبانی استعلام دردسترس
                        ScenarioOptionCard(
                            title = "فروشگاه فعال و پشتیبانی استعلام دردسترس",
                            description = "فروشگاه باز است و استعلام‌های فوری خریداران همراه با زنگ تماس ارسال می‌شود.",
                            isSelected = currentScenario == 1,
                            accentColor = TorobGreen,
                            onClick = {
                                viewModel.updateProfile(ShopUpdateDto(isOpen = true, acceptInquiries = true))
                            }
                        )

                        Spacer(modifier = Modifier.height(10.dp))

                        // Scenario 2: فروشگاه فعال اما پشتیبانی استعلام غیرفعال
                        ScenarioOptionCard(
                            title = "فروشگاه فعال اما پشتیبانی استعلام غیرفعال",
                            description = "فروشگاه در ترب باز است اما استعلام فوری دریافت نمی‌شود.",
                            isSelected = currentScenario == 2,
                            accentColor = TorobAmber,
                            onClick = {
                                viewModel.updateProfile(ShopUpdateDto(isOpen = true, acceptInquiries = false))
                            }
                        )

                        Spacer(modifier = Modifier.height(10.dp))

                        // Scenario 3: فروشگاه غیرفعال و بسته
                        ScenarioOptionCard(
                            title = "فروشگاه غیرفعال و بسته",
                            description = "فروشگاه کاملاً غیرفعال است و هیچ استعلامی ارسال نخواهد شد.",
                            isSelected = currentScenario == 3,
                            accentColor = TorobRed,
                            onClick = {
                                viewModel.updateProfile(ShopUpdateDto(isOpen = false, acceptInquiries = false))
                            }
                        )
                    }
                }

                // Outside Working Hours Banner
                if (shop != null && !shop.isWithinWorkingHours) {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(containerColor = TorobLightAmber),
                        border = BorderStroke(1.dp, TorobAmber.copy(alpha = 0.3f))
                    ) {
                        Row(
                            modifier = Modifier.padding(14.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                imageVector = Icons.Default.Schedule,
                                contentDescription = null,
                                tint = TorobAmber,
                                modifier = Modifier.size(24.dp)
                            )
                            Spacer(modifier = Modifier.width(12.dp))
                            Column {
                                Text(
                                    text = "هم‌اکنون در ساعات غیرکاری هستید",
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Slate900
                                )
                                Spacer(modifier = Modifier.height(2.dp))
                                Text(
                                    text = "ساعت کاری فروشگاه: ${shop.openTime} الی ${shop.closeTime}. در ساعات غیرکاری، استعلام جدید ارسال نمی‌شود و وضعیت فروشگاه بسته خواهد بود.",
                                    fontSize = 11.sp,
                                    color = Slate700,
                                    lineHeight = 16.sp
                                )
                            }
                        }
                    }
                }

                // Error Message Alert
                if (state.errorMessage != null) {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(containerColor = TorobLightRed),
                        border = BorderStroke(1.dp, TorobRed.copy(alpha = 0.3f))
                    ) {
                        Row(
                            modifier = Modifier.padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                imageVector = Icons.Default.ErrorOutline,
                                contentDescription = null,
                                tint = TorobRed,
                                modifier = Modifier.size(20.dp)
                            )
                            Spacer(modifier = Modifier.width(10.dp))
                            Text(
                                text = state.errorMessage!!,
                                color = TorobRed,
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }

                // Success Message Alert
                if (state.successMessage != null) {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(containerColor = TorobLightGreen),
                        border = BorderStroke(1.dp, TorobGreen.copy(alpha = 0.3f))
                    ) {
                        Row(
                            modifier = Modifier.padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                imageVector = Icons.Default.CheckCircleOutline,
                                contentDescription = null,
                                tint = TorobGreen,
                                modifier = Modifier.size(20.dp)
                            )
                            Spacer(modifier = Modifier.width(10.dp))
                            Text(
                                text = state.successMessage!!,
                                color = TorobGreen,
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }

                // Request Alert Messages
                if (state.requestSuccessMessage != null) {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(containerColor = TorobLightGreen),
                        border = BorderStroke(1.dp, TorobGreen.copy(alpha = 0.3f))
                    ) {
                        Row(
                            modifier = Modifier.padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                imageVector = Icons.Default.CheckCircleOutline,
                                contentDescription = null,
                                tint = TorobGreen,
                                modifier = Modifier.size(20.dp)
                            )
                            Spacer(modifier = Modifier.width(10.dp))
                            Text(
                                text = state.requestSuccessMessage!!,
                                color = TorobGreen,
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }

                if (state.requestErrorMessage != null) {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(containerColor = TorobLightRed),
                        border = BorderStroke(1.dp, TorobRed.copy(alpha = 0.3f))
                    ) {
                        Row(
                            modifier = Modifier.padding(12.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                imageVector = Icons.Default.ErrorOutline,
                                contentDescription = null,
                                tint = TorobRed,
                                modifier = Modifier.size(20.dp)
                            )
                            Spacer(modifier = Modifier.width(10.dp))
                            Text(
                                text = state.requestErrorMessage!!,
                                color = TorobRed,
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }

                // Pending Change Request Banner
                val latestReq = state.latestChangeRequest
                if (latestReq != null && latestReq.status == "PENDING") {
                    Card(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(14.dp),
                        colors = CardDefaults.cardColors(containerColor = TorobLightAmber),
                        border = BorderStroke(1.dp, TorobAmber.copy(alpha = 0.5f))
                    ) {
                        Column(modifier = Modifier.padding(14.dp)) {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(
                                    imageVector = Icons.Default.HourglassTop,
                                    contentDescription = null,
                                    tint = TorobAmber,
                                    modifier = Modifier.size(20.dp)
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(
                                    text = "درخواست تغییر اطلاعات در انتظار بررسی پشتیبانی",
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Slate900
                                )
                            }
                            Spacer(modifier = Modifier.height(6.dp))
                            Text(
                                text = "درخواست رسمی شما برای ویرایش مشخصات فروشگاه ثبت گردیده و در حال حاضر توسط تیم پشتیبانی ترب در صف بررسی قرار دارد. پس از تایید، تغییرات به صورت خودکار اعمال خواهند شد.",
                                fontSize = 11.sp,
                                color = Slate700,
                                lineHeight = 16.sp
                            )
                        }
                    }
                }

                // Locked General Store Info Card
                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .border(1.dp, MaterialTheme.colorScheme.outline, RoundedCornerShape(16.dp)),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "مشخصات عمومی فروشگاه",
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                            Surface(
                                shape = RoundedCornerShape(16.dp),
                                color = MaterialTheme.colorScheme.surfaceVariant,
                                border = BorderStroke(1.dp, MaterialTheme.colorScheme.outline)
                            ) {
                                Row(
                                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(4.dp)
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.Lock,
                                        contentDescription = null,
                                        tint = MaterialTheme.colorScheme.onSurfaceVariant,
                                        modifier = Modifier.size(12.dp)
                                    )
                                    Text(
                                        text = "قفل شده امنیتی",
                                        fontSize = 10.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                }
                            }
                        }

                        Text(
                            text = "به منظور حفظ امنیت و اصالت داده‌ها، تغییر نام، تلفن، آدرس و ساعات کاری صرفاً از طریق تایید پشتیبانی ترب امکان‌پذیر است.",
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            lineHeight = 16.sp
                        )

                        OutlinedTextField(
                            value = shop?.shopName ?: "",
                            onValueChange = {},
                            readOnly = true,
                            label = { Text("نام فروشگاه") },
                            trailingIcon = {
                                Icon(Icons.Default.Lock, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.size(16.dp))
                            },
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedBorderColor = MaterialTheme.colorScheme.outline,
                                unfocusedBorderColor = MaterialTheme.colorScheme.outline,
                                focusedContainerColor = MaterialTheme.colorScheme.surfaceVariant,
                                unfocusedContainerColor = MaterialTheme.colorScheme.surfaceVariant,
                                focusedTextColor = MaterialTheme.colorScheme.onSurface,
                                unfocusedTextColor = MaterialTheme.colorScheme.onSurface
                            ),
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp)
                        )

                        OutlinedTextField(
                            value = shop?.phone ?: "",
                            onValueChange = {},
                            readOnly = true,
                            label = { Text("تلفن تماس فروشگاه") },
                            trailingIcon = {
                                Icon(Icons.Default.Lock, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.size(16.dp))
                            },
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedBorderColor = MaterialTheme.colorScheme.outline,
                                unfocusedBorderColor = MaterialTheme.colorScheme.outline,
                                focusedContainerColor = MaterialTheme.colorScheme.surfaceVariant,
                                unfocusedContainerColor = MaterialTheme.colorScheme.surfaceVariant,
                                focusedTextColor = MaterialTheme.colorScheme.onSurface,
                                unfocusedTextColor = MaterialTheme.colorScheme.onSurface
                            ),
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp)
                        )

                        OutlinedTextField(
                            value = shop?.address ?: "",
                            onValueChange = {},
                            readOnly = true,
                            label = { Text("آدرس دقیق فروشگاه در تهران") },
                            trailingIcon = {
                                Icon(Icons.Default.Lock, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.size(16.dp))
                            },
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedBorderColor = MaterialTheme.colorScheme.outline,
                                unfocusedBorderColor = MaterialTheme.colorScheme.outline,
                                focusedContainerColor = MaterialTheme.colorScheme.surfaceVariant,
                                unfocusedContainerColor = MaterialTheme.colorScheme.surfaceVariant,
                                focusedTextColor = MaterialTheme.colorScheme.onSurface,
                                unfocusedTextColor = MaterialTheme.colorScheme.onSurface
                            ),
                            modifier = Modifier.fillMaxWidth(),
                            minLines = 2,
                            shape = RoundedCornerShape(12.dp)
                        )

                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            OutlinedTextField(
                                value = shop?.openTime ?: "09:00",
                                onValueChange = {},
                                readOnly = true,
                                label = { Text("ساعت بازگشایی (HH:MM)") },
                                trailingIcon = {
                                    Icon(Icons.Default.Lock, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.size(16.dp))
                                },
                                colors = OutlinedTextFieldDefaults.colors(
                                    focusedBorderColor = MaterialTheme.colorScheme.outline,
                                    unfocusedBorderColor = MaterialTheme.colorScheme.outline,
                                    focusedContainerColor = MaterialTheme.colorScheme.surfaceVariant,
                                    unfocusedContainerColor = MaterialTheme.colorScheme.surfaceVariant,
                                    focusedTextColor = MaterialTheme.colorScheme.onSurface,
                                    unfocusedTextColor = MaterialTheme.colorScheme.onSurface
                                ),
                                modifier = Modifier.weight(1f),
                                shape = RoundedCornerShape(12.dp)
                            )
                            OutlinedTextField(
                                value = shop?.closeTime ?: "21:00",
                                onValueChange = {},
                                readOnly = true,
                                label = { Text("ساعت پایان کار (HH:MM)") },
                                trailingIcon = {
                                    Icon(Icons.Default.Lock, contentDescription = null, tint = MaterialTheme.colorScheme.onSurfaceVariant, modifier = Modifier.size(16.dp))
                                },
                                colors = OutlinedTextFieldDefaults.colors(
                                    focusedBorderColor = MaterialTheme.colorScheme.outline,
                                    unfocusedBorderColor = MaterialTheme.colorScheme.outline,
                                    focusedContainerColor = MaterialTheme.colorScheme.surfaceVariant,
                                    unfocusedContainerColor = MaterialTheme.colorScheme.surfaceVariant,
                                    focusedTextColor = MaterialTheme.colorScheme.onSurface,
                                    unfocusedTextColor = MaterialTheme.colorScheme.onSurface
                                ),
                                modifier = Modifier.weight(1f),
                                shape = RoundedCornerShape(12.dp)
                            )
                        }

                        val isPending = latestReq?.status == "PENDING"
                        Button(
                            onClick = {
                                reqShopName = shop?.shopName ?: ""
                                reqPhone = shop?.phone ?: ""
                                reqAddress = shop?.address ?: ""
                                reqOpenTime = shop?.openTime ?: "09:00"
                                reqCloseTime = shop?.closeTime ?: "21:00"
                                reqReason = ""
                                viewModel.clearRequestMessages()
                                showRequestDialog = true
                            },
                            enabled = !isPending && !state.isSubmittingRequest,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(48.dp),
                            colors = ButtonDefaults.buttonColors(
                                containerColor = if (isPending) Slate300 else TorobRed,
                                contentColor = PureWhite
                            ),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                Icon(
                                    imageVector = if (isPending) Icons.Default.HourglassTop else Icons.Default.SupportAgent,
                                    contentDescription = null,
                                    modifier = Modifier.size(18.dp)
                                )
                                Text(
                                    text = if (isPending) "درخواست تغییر در حال بررسی است" else "درخواست تغییر اطلاعات به پشتیبانی",
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = PureWhite
                                )
                            }
                        }
                    }
                }
            }
        }
    }

    // Support Request Dialog
    if (showRequestDialog) {
        AlertDialog(
            onDismissRequest = {
                if (!state.isSubmittingRequest) showRequestDialog = false
            },
            title = {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.SupportAgent,
                        contentDescription = null,
                        tint = TorobRed,
                        modifier = Modifier.size(24.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "درخواست تغییر مشخصات به پشتیبانی",
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        color = Slate900
                    )
                }
            },
            text = {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text(
                        text = "اطلاعات جدید مورد نظر خود را وارد کنید. این اطلاعات پس از بررسی و تایید کارشناسان ترب روی فروشگاه شما اعمال خواهد شد.",
                        fontSize = 11.sp,
                        color = Slate600,
                        lineHeight = 16.sp
                    )

                    OutlinedTextField(
                        value = reqShopName,
                        onValueChange = { reqShopName = it },
                        label = { Text("نام پیشنهادی فروشگاه") },
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(10.dp)
                    )

                    OutlinedTextField(
                        value = reqPhone,
                        onValueChange = { reqPhone = it },
                        label = { Text("شماره تلفن جدید فروشگاه") },
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(10.dp)
                    )

                    OutlinedTextField(
                        value = reqAddress,
                        onValueChange = { reqAddress = it },
                        label = { Text("آدرس دقیق جدید") },
                        modifier = Modifier.fillMaxWidth(),
                        minLines = 2,
                        shape = RoundedCornerShape(10.dp)
                    )

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        OutlinedTextField(
                            value = reqOpenTime,
                            onValueChange = { reqOpenTime = it },
                            label = { Text("ساعت بازگشایی") },
                            modifier = Modifier.weight(1f),
                            shape = RoundedCornerShape(10.dp)
                        )
                        OutlinedTextField(
                            value = reqCloseTime,
                            onValueChange = { reqCloseTime = it },
                            label = { Text("ساعت پایان کار") },
                            modifier = Modifier.weight(1f),
                            shape = RoundedCornerShape(10.dp)
                        )
                    }

                    OutlinedTextField(
                        value = reqReason,
                        onValueChange = { reqReason = it },
                        label = { Text("علت یا توضیحات درخواست (اختیاری)") },
                        modifier = Modifier.fillMaxWidth(),
                        minLines = 2,
                        shape = RoundedCornerShape(10.dp)
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        viewModel.submitChangeRequest(
                            ShopChangeRequestCreateDto(
                                requestedShopName = reqShopName.ifBlank { null },
                                requestedPhone = reqPhone.ifBlank { null },
                                requestedAddress = reqAddress.ifBlank { null },
                                requestedOpenTime = reqOpenTime.ifBlank { null },
                                requestedCloseTime = reqCloseTime.ifBlank { null },
                                reason = reqReason.ifBlank { null }
                            )
                        ) { success ->
                            if (success) {
                                showRequestDialog = false
                            }
                        }
                    },
                    enabled = !state.isSubmittingRequest,
                    colors = ButtonDefaults.buttonColors(containerColor = TorobRed),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    if (state.isSubmittingRequest) {
                        CircularProgressIndicator(color = PureWhite, modifier = Modifier.size(16.dp))
                    } else {
                        Text("ارسال به پشتیبانی", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = PureWhite)
                    }
                }
            },
            dismissButton = {
                TextButton(
                    onClick = { showRequestDialog = false },
                    enabled = !state.isSubmittingRequest
                ) {
                    Text("انصراف", fontSize = 12.sp, color = Slate600)
                }
            },
            shape = RoundedCornerShape(16.dp)
        )
    }
}

@Composable
private fun ScenarioOptionCard(
    title: String,
    description: String,
    isSelected: Boolean,
    accentColor: Color,
    onClick: () -> Unit
) {
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(12.dp),
        color = if (isSelected) accentColor.copy(alpha = 0.08f) else MaterialTheme.colorScheme.surfaceVariant,
        border = BorderStroke(
            width = if (isSelected) 1.5.dp else 1.dp,
            color = if (isSelected) accentColor else MaterialTheme.colorScheme.outline
        ),
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier.padding(14.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            RadioButton(
                selected = isSelected,
                onClick = onClick,
                colors = RadioButtonDefaults.colors(
                    selectedColor = accentColor,
                    unselectedColor = MaterialTheme.colorScheme.onSurfaceVariant
                )
            )
            Spacer(modifier = Modifier.width(10.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = title,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold,
                    color = if (isSelected) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant
                )
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = description,
                    fontSize = 11.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    lineHeight = 16.sp
                )
            }
        }
    }
}
