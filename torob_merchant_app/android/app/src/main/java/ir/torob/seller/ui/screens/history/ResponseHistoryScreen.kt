package ir.torob.seller.ui.screens.history

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.CloudOff
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ir.torob.seller.data.local.InquiryEntity
import ir.torob.seller.ui.components.ConnectionStatusBar
import ir.torob.seller.ui.components.EmptyStateView
import ir.torob.seller.ui.components.InquiryStatusBadge
import ir.torob.seller.ui.components.ProductThumbnail
import ir.torob.seller.ui.theme.*
import ir.torob.seller.ui.viewmodel.InquiryViewModel
import ir.torob.seller.util.PersianFormatters

@Composable
fun ResponseHistoryScreen(
    viewModel: InquiryViewModel,
    isOnline: Boolean,
    onInquiryClick: (String) -> Unit
) {
    val historyList by viewModel.historyInquiries.collectAsState()
    val historyFilter by viewModel.historyFilter.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val isServerConnected by viewModel.isServerConnected.collectAsState()
    val listState = rememberLazyListState()
    val focusManager = LocalFocusManager.current

    var searchQuery by remember { mutableStateOf("") }

    LaunchedEffect(Unit) {
        viewModel.refresh()
    }

    LaunchedEffect(historyFilter) {
        listState.scrollToItem(0)
    }

    val filteredList = remember(historyList, searchQuery) {
        if (searchQuery.isBlank()) {
            historyList
        } else {
            val q = searchQuery.trim().lowercase()
            historyList.filter {
                it.productTitle.lowercase().contains(q) ||
                it.trackingCode.lowercase().contains(q) ||
                it.customerName.lowercase().contains(q)
            }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
    ) {
        ConnectionStatusBar(isOnline = isOnline)

        // Top App Bar
        Surface(
            modifier = Modifier.fillMaxWidth(),
            color = MaterialTheme.colorScheme.surface,
            shadowElevation = 1.dp
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 14.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "تاریخچه استعلام‌ها",
                        fontSize = 19.sp,
                        fontWeight = FontWeight.Black,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Spacer(modifier = Modifier.height(2.dp))
                    Text(
                        text = "آرشیو استعلام‌های پاسخ‌داده‌شده، ناموجود، ردشده و منقضی",
                        fontSize = 11.sp,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                FilledTonalButton(
                    onClick = viewModel::refresh,
                    colors = ButtonDefaults.filledTonalButtonColors(
                        containerColor = MaterialTheme.colorScheme.surfaceVariant,
                        contentColor = MaterialTheme.colorScheme.onSurface
                    ),
                    contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp),
                    shape = RoundedCornerShape(10.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Refresh,
                        contentDescription = "بروزرسانی",
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = "بروزرسانی",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
        }

        // Live Search Bar
        Surface(
            modifier = Modifier.fillMaxWidth(),
            color = MaterialTheme.colorScheme.surface,
            shadowElevation = 0.5.dp
        ) {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp)
            ) {
                OutlinedTextField(
                    value = searchQuery,
                    onValueChange = { searchQuery = it },
                    placeholder = {
                        Text(
                            text = "جستجو در نام کالا، کد رهگیری یا نام خریدار...",
                            fontSize = 12.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    },
                    leadingIcon = {
                        Icon(
                            imageVector = Icons.Default.Search,
                            contentDescription = "جستجو",
                            tint = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.size(20.dp)
                        )
                    },
                    trailingIcon = {
                        if (searchQuery.isNotEmpty()) {
                            IconButton(onClick = { searchQuery = "" }) {
                                Icon(
                                    imageVector = Icons.Default.Clear,
                                    contentDescription = "پاک کردن",
                                    tint = MaterialTheme.colorScheme.onSurfaceVariant,
                                    modifier = Modifier.size(18.dp)
                                )
                            }
                        }
                    },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                    keyboardActions = KeyboardActions(onSearch = { focusManager.clearFocus() }),
                    shape = RoundedCornerShape(12.dp),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedBorderColor = TorobRed,
                        unfocusedBorderColor = MaterialTheme.colorScheme.outline,
                        focusedContainerColor = MaterialTheme.colorScheme.surfaceVariant,
                        unfocusedContainerColor = MaterialTheme.colorScheme.surfaceVariant,
                        focusedTextColor = MaterialTheme.colorScheme.onSurface,
                        unfocusedTextColor = MaterialTheme.colorScheme.onSurface
                    ),
                    modifier = Modifier.fillMaxWidth()
                )
            }
        }

        // Filter Tabs (همه، پاسخ‌داده‌شده، عدم موجودی، رد استعلام، منقضی‌شده)
        val filterScrollState = rememberScrollState()
        Surface(
            modifier = Modifier.fillMaxWidth(),
            color = MaterialTheme.colorScheme.surface,
            shadowElevation = 0.5.dp
        ) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(filterScrollState)
                    .padding(horizontal = 16.dp, vertical = 8.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                ModernFilterChip(
                    title = "همه",
                    isSelected = historyFilter == "ALL",
                    onClick = { viewModel.setHistoryFilter("ALL") }
                )
                ModernFilterChip(
                    title = "پاسخ‌داده‌شده",
                    isSelected = historyFilter == "ANSWERED",
                    onClick = { viewModel.setHistoryFilter("ANSWERED") }
                )
                ModernFilterChip(
                    title = "عدم موجودی",
                    isSelected = historyFilter == "OUT_OF_STOCK",
                    onClick = { viewModel.setHistoryFilter("OUT_OF_STOCK") }
                )
                ModernFilterChip(
                    title = "رد استعلام",
                    isSelected = historyFilter == "DECLINED",
                    onClick = { viewModel.setHistoryFilter("DECLINED") }
                )
                ModernFilterChip(
                    title = "منقضی‌شده",
                    isSelected = historyFilter == "EXPIRED",
                    onClick = { viewModel.setHistoryFilter("EXPIRED") }
                )
            }
        }

        // Content Area
        when {
            isLoading && historyList.isEmpty() -> {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator(color = TorobRed)
                }
            }

            !isOnline || !isServerConnected -> {
                EmptyStateView(
                    icon = Icons.Default.CloudOff,
                    iconTint = TorobError,
                    iconBgColor = TorobErrorLight,
                    title = "ارتباط با سرور ترب برقرار نیست",
                    description = "جهت حفظ امنیت و محرمانگی، مشاهده تاریخچه استعلام‌ها تنها در زمان برقراری ارتباط با سرور امکان‌پذیر است.",
                    actionButtonText = "تلاش مجدد برای اتصال",
                    onActionClick = viewModel::refresh,
                    modifier = Modifier.fillMaxSize()
                )
            }

            historyList.isEmpty() -> {
                EmptyStateView(
                    icon = Icons.Default.History,
                    iconTint = TorobRed,
                    iconBgColor = TorobRedLight,
                    title = when (historyFilter) {
                        "ANSWERED" -> "هیچ استعلام پاسخ‌داده‌شده‌ای یافت نشد"
                        "OUT_OF_STOCK" -> "هیچ استعلام با عدم موجودی یافت نشد"
                        "DECLINED" -> "هیچ استعلام ردشده‌ای ثبت نشده است"
                        "EXPIRED" -> "هیچ استعلام منقضی‌شده‌ای وجود ندارد"
                        else -> "تاریخچه استعلام‌های شما خالی است"
                    },
                    description = "پاسخ‌هایی که به خریداران در ترب ارسال می‌کنید پس از ثبت در این بخش نگهداری می‌شوند.",
                    actionButtonText = if (historyFilter != "ALL") "مشاهده همه" else null,
                    onActionClick = { viewModel.setHistoryFilter("ALL") },
                    modifier = Modifier.fillMaxSize()
                )
            }

            filteredList.isEmpty() && searchQuery.isNotEmpty() -> {
                EmptyStateView(
                    icon = Icons.Default.Search,
                    iconTint = TorobTextSecondary,
                    iconBgColor = TorobBackground,
                    title = "نتیجه‌ای یافت نشد",
                    description = "استعلامی متناسب با عبارت «$searchQuery» پیدا نشد.",
                    actionButtonText = "پاک کردن جستجو",
                    onActionClick = { searchQuery = "" },
                    modifier = Modifier.fillMaxSize()
                )
            }

            else -> {
                LazyColumn(
                    state = listState,
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(filteredList, key = { it.inquiryId }) { inq ->
                        ModernHistoryCard(
                            inquiry = inq,
                            onClick = { onInquiryClick(inq.inquiryId) }
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun ModernFilterChip(
    title: String,
    isSelected: Boolean,
    onClick: () -> Unit
) {
    Surface(
        onClick = onClick,
        shape = RoundedCornerShape(10.dp),
        color = if (isSelected) TorobRed else MaterialTheme.colorScheme.surfaceVariant,
        border = if (isSelected) null else androidx.compose.foundation.BorderStroke(1.dp, MaterialTheme.colorScheme.outline)
    ) {
        Box(
            modifier = Modifier.padding(horizontal = 14.dp, vertical = 7.dp),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = title,
                color = if (isSelected) PureWhite else MaterialTheme.colorScheme.onSurfaceVariant,
                fontSize = 12.sp,
                fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium
            )
        }
    }
}

@Composable
private fun ModernHistoryCard(
    inquiry: InquiryEntity,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .border(1.dp, MaterialTheme.colorScheme.outline, RoundedCornerShape(16.dp)),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.5.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            // Header Row: Tracking Code & Status
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "کد رهگیری: ${inquiry.trackingCode}",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                InquiryStatusBadge(status = inquiry.status)
            }

            Spacer(modifier = Modifier.height(10.dp))

            // Body: Thumbnail + Product title + Customer
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.Top,
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                ProductThumbnail(
                    imageUrl = inquiry.productImageUrl,
                    contentDescription = inquiry.productTitle,
                    size = 56.dp,
                    cornerRadius = 10.dp
                )

                Column(
                    modifier = Modifier.weight(1f),
                    verticalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    Text(
                        text = inquiry.productTitle,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurface,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis
                    )

                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Person,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.size(13.dp)
                        )
                        Text(
                            text = "خریدار: ${inquiry.customerName}",
                            fontSize = 11.sp,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(10.dp))
            HorizontalDivider(color = MaterialTheme.colorScheme.outline, thickness = 0.8.dp)
            Spacer(modifier = Modifier.height(8.dp))

            // Price Details
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "قیمت مرجع: ${PersianFormatters.formatPriceToman(inquiry.recordedPriceToman)}",
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSurface
                )

                Text(
                    text = "مشاهده جزئیات ←",
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    color = TorobRed
                )
            }

            if (!inquiry.userNote.isNullOrBlank()) {
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = "«${inquiry.userNote}»",
                    fontSize = 11.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }

            // Status-specific feedback banner
            if (inquiry.status == "DECLINED") {
                val reasonText = inquiry.declineReason ?: inquiry.responseNotes ?: "مشخص نشده"
                Surface(
                    color = TorobErrorLight,
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 8.dp)
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Clear,
                            contentDescription = null,
                            tint = TorobError,
                            modifier = Modifier.size(14.dp)
                        )
                        Text(
                            text = "علت رد استعلام: $reasonText",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = TorobError
                        )
                    }
                }
            } else if (inquiry.status == "OUT_OF_STOCK") {
                Surface(
                    color = TorobWarningLight,
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 8.dp)
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Clear,
                            contentDescription = null,
                            tint = WarningAmberDark,
                            modifier = Modifier.size(14.dp)
                        )
                        Text(
                            text = "اعلام عدم موجودی کالا در انبار توسط فروشگاه",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = WarningAmberDark
                        )
                    }
                }
            } else if (inquiry.status == "ANSWERED" && inquiry.responsePrice != null && inquiry.responsePrice > 0) {
                Surface(
                    color = TorobSuccessLight,
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 8.dp)
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        Text(
                            text = "قیمت پیشنهادی شما: ${PersianFormatters.formatPriceToman(inquiry.responsePrice)}",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = TorobSuccess
                        )
                    }
                }
            }
        }
    }
}
