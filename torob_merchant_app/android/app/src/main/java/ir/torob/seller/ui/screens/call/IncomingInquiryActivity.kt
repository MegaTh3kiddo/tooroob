package ir.torob.seller.ui.screens.call

import android.app.KeyguardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.view.WindowManager
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.*
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import coil.request.ImageRequest
import ir.torob.seller.MainActivity
import ir.torob.seller.data.local.InquiryEntity
import ir.torob.seller.data.model.ShopUpdateDto
import ir.torob.seller.data.repository.InquiryRepository
import ir.torob.seller.data.repository.ShopRepository
import ir.torob.seller.service.InquiryAlertService
import ir.torob.seller.ui.theme.*
import ir.torob.seller.util.InquiryRingtoneManager
import ir.torob.seller.util.PersianFormatters
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

enum class DeclineReason(val code: String, val title: String, val description: String) {
    STORE_CLOSED(
        code = "STORE_CLOSED",
        title = "فروشگاه در حال حاضر بسته است",
        description = "فروشگاه در حال حاضر تعطیل است یا امکان ارائه خدمت ندارد"
    ),
    PRODUCT_NOT_SUPPORTED(
        code = "PRODUCT_NOT_SUPPORTED",
        title = "این محصول در فروشگاه ارائه نمیشود",
        description = "عدم تامین یا توقف فروش این قلم کالا توسط فروشگاه"
    ),
    BUSY(
        code = "BUSY",
        title = "امکان بررسی قیمت را ندارم",
        description = "به دلیل حجم کاری بالا یا عدم دسترسی به موجودی دقیق در حال حاضر مقدور نیست"
    ),
    WRONG_PRODUCT(
        code = "WRONG_PRODUCT",
        title = "درخواست اشتباه است",
        description = "مشخصات یا تنوع کالا با محصول عرضه شده در فروشگاه مطابقت ندارد"
    ),
    OTHER(
        code = "OTHER",
        title = "سایر موارد",
        description = "دلیل دیگری که در گزینه‌های فوق ذکر نشده است"
    )
}

class IncomingInquiryActivity : ComponentActivity() {

    private var currentInquiryId by mutableStateOf("inq_01")
    private var currentFallbackTitle by mutableStateOf("استعلام جدید خریدار")
    private var currentFallbackBody by mutableStateOf("خریدار منتظر پاسخ قیمت و موجودی شماست")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Wake screen and turn on over lockscreen
        turnScreenOnAndDismissKeyguard()

        extractIntentExtras(intent)

        setContent {
            CompositionLocalProvider(
                LocalLayoutDirection provides LayoutDirection.Rtl,
                LocalTextStyle provides TextStyle(fontFamily = VazirFontFamily)
            ) {
                SmartInquiryCallScreen(
                    inquiryId = currentInquiryId,
                    fallbackTitle = currentFallbackTitle,
                    fallbackBody = currentFallbackBody,
                    onAnswer = {
                        stopRingingAndAlert()
                        val mainIntent = Intent(this, MainActivity::class.java).apply {
                            action = Intent.ACTION_VIEW
                            data = Uri.parse("torob://inquiry/$currentInquiryId")
                            putExtra("inquiry_id", currentInquiryId)
                            flags = Intent.FLAG_ACTIVITY_NEW_TASK or
                                    Intent.FLAG_ACTIVITY_CLEAR_TOP or
                                    Intent.FLAG_ACTIVITY_SINGLE_TOP
                        }
                        startActivity(mainIntent)
                        finish()
                    },
                    onQuickConfirmPrice = { price ->
                        stopRingingAndAlert()
                        CoroutineScope(Dispatchers.IO).launch {
                            try {
                                InquiryRepository(applicationContext).submitResponse(
                                    inquiryId = currentInquiryId,
                                    priceToman = price,
                                    inStock = true,
                                    stockCount = 1,
                                    notes = "تأیید سریع قیمت ثبت‌شده قبلی"
                                )
                                withContext(Dispatchers.Main) {
                                    Toast.makeText(applicationContext, "قیمت قبلی با موفقیت تأیید و ارسال شد", Toast.LENGTH_SHORT).show()
                                    finish()
                                }
                            } catch (_: Exception) {
                                withContext(Dispatchers.Main) {
                                    finish()
                                }
                            }
                        }
                    },
                    onOutOfStock = {
                        stopRingingAndAlert()
                        CoroutineScope(Dispatchers.IO).launch {
                            try {
                                InquiryRepository(applicationContext).submitResponse(
                                    inquiryId = currentInquiryId,
                                    priceToman = 0L,
                                    inStock = false,
                                    stockCount = 0,
                                    notes = "عدم موجودی در انبار",
                                    status = "OUT_OF_STOCK"
                                )
                                withContext(Dispatchers.Main) {
                                    Toast.makeText(applicationContext, "عدم موجودی کالا ثبت شد", Toast.LENGTH_SHORT).show()
                                    finish()
                                }
                            } catch (_: Exception) {
                                withContext(Dispatchers.Main) {
                                    finish()
                                }
                            }
                        }
                    },
                    onConfirmDecline = { reason, customNote, closeShop ->
                        stopRingingAndAlert()
                        CoroutineScope(Dispatchers.IO).launch {
                            try {
                                val declineTitle = if (customNote.isNotBlank()) "${reason.title} - $customNote" else reason.title
                                val declineNote = buildString {
                                    append("رد استعلام: [${reason.code}] ${reason.title}")
                                    if (customNote.isNotBlank()) {
                                        append(" - $customNote")
                                    }
                                }
                                InquiryRepository(applicationContext).submitResponse(
                                    inquiryId = currentInquiryId,
                                    priceToman = 0L,
                                    inStock = false,
                                    stockCount = 0,
                                    notes = declineNote,
                                    status = "DECLINED",
                                    declineReason = declineTitle
                                )
                                if (closeShop && reason == DeclineReason.STORE_CLOSED) {
                                    ShopRepository(applicationContext).updateShopProfile(
                                        ShopUpdateDto(isOpen = false)
                                    )
                                }
                                withContext(Dispatchers.Main) {
                                    Toast.makeText(applicationContext, "استعلام با موفقیت رد شد", Toast.LENGTH_SHORT).show()
                                    finish()
                                }
                            } catch (_: Exception) {
                                withContext(Dispatchers.Main) {
                                    finish()
                                }
                            }
                        }
                    },
                    onDismiss = {
                        stopRingingAndAlert()
                        finish()
                    }
                )
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        extractIntentExtras(intent)
    }

    private fun extractIntentExtras(intent: Intent) {
        currentInquiryId = intent.getStringExtra("inquiry_id") ?: "inq_01"
        currentFallbackTitle = intent.getStringExtra("title") ?: "استعلام جدید خریدار"
        currentFallbackBody = intent.getStringExtra("body") ?: "خریدار منتظر پاسخ قیمت و موجودی شماست"
    }

    private fun turnScreenOnAndDismissKeyguard() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true)
            setTurnScreenOn(true)
            val keyguardManager = getSystemService(Context.KEYGUARD_SERVICE) as KeyguardManager
            keyguardManager.requestDismissKeyguard(this, null)
        } else {
            @Suppress("DEPRECATION")
            window.addFlags(
                WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or
                WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD or
                WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON or
                WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
            )
        }
    }

    private fun stopRingingAndAlert() {
        InquiryRingtoneManager.stopRinging(applicationContext)
        try {
            val stopIntent = Intent(this, InquiryAlertService::class.java).apply {
                action = InquiryAlertService.ACTION_STOP_ALERT
            }
            startService(stopIntent)
        } catch (_: Exception) {}
        try {
            stopService(Intent(this, InquiryAlertService::class.java))
        } catch (_: Exception) {}
    }

    @Suppress("DEPRECATION")
    override fun onBackPressed() {
        stopRingingAndAlert()
        super.onBackPressed()
    }

    override fun onDestroy() {
        stopRingingAndAlert()
        super.onDestroy()
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SmartInquiryCallScreen(
    inquiryId: String,
    fallbackTitle: String,
    fallbackBody: String,
    onAnswer: () -> Unit,
    onQuickConfirmPrice: (Long) -> Unit,
    onOutOfStock: () -> Unit,
    onConfirmDecline: (DeclineReason, String, Boolean) -> Unit,
    onDismiss: () -> Unit
) {
    val context = LocalContext.current
    var inquiry by remember { mutableStateOf<InquiryEntity?>(null) }
    var remainingSeconds by remember { mutableLongStateOf(120L) }
    var isSubmitting by remember { mutableStateOf(false) }

    // Bottom Sheet for Declining Inquiry
    var showDeclineSheet by remember { mutableStateOf(false) }
    var selectedDeclineReason by remember { mutableStateOf<DeclineReason?>(null) }
    var customDeclineNote by remember { mutableStateOf("") }
    var closeShopOnDecline by remember { mutableStateOf(false) }

    // Load full inquiry data from Repository
    LaunchedEffect(inquiryId) {
        val repo = InquiryRepository(context)
        val item = repo.getInquiryById(inquiryId)
        if (item != null) {
            inquiry = item
            if (item.remainingSeconds > 0) {
                remainingSeconds = minOf(120L, item.remainingSeconds)
            }
        }
    }

    // Ticking countdown timer
    LaunchedEffect(remainingSeconds) {
        if (remainingSeconds > 0) {
            delay(1000L)
            remainingSeconds -= 1
        } else {
            onDismiss()
        }
    }

    // Pulsing indicator for live inquiry effect
    val infiniteTransition = rememberInfiniteTransition(label = "pulse")
    val pulseAlpha by infiniteTransition.animateFloat(
        initialValue = 0.35f,
        targetValue = 1f,
        animationSpec = infiniteRepeatable(
            animation = tween(900, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Reverse
        ),
        label = "pulseAlpha"
    )

    val productTitle = inquiry?.productTitle ?: fallbackTitle
    val trackingCode = inquiry?.trackingCode ?: "TRB-NEW"
    val recordedPrice = inquiry?.recordedPriceToman ?: 0L
    val buyerNote = inquiry?.userNote ?: fallbackBody
    val customerName = inquiry?.customerName ?: "خریدار در ترب"
    val categoryName = inquiry?.categoryName ?: "کالای دیجیتال"
    val imageUrl = inquiry?.productImageUrl

    val isUrgent = remainingSeconds <= 180

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                Brush.verticalGradient(
                    colors = listOf(
                        Color(0xFF070B14),
                        Color(0xFF0F172A),
                        Color(0xFF1E293B)
                    )
                )
            )
            .statusBarsPadding()
            .navigationBarsPadding()
            .padding(horizontal = 20.dp, vertical = 16.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState()),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            // --- TOP HEADER: Status badge, tracking code, live countdown timer ---
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    // Live Inquiry Pulsing Badge
                    Surface(
                        shape = RoundedCornerShape(20.dp),
                        color = Color(0xFF1E293B),
                        border = BorderStroke(1.dp, PrimaryBlue.copy(alpha = 0.6f))
                    ) {
                        Row(
                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(9.dp)
                                    .scale(1f)
                                    .clip(CircleShape)
                                    .background(PrimaryBlueHover.copy(alpha = pulseAlpha))
                            )
                            Spacer(modifier = Modifier.width(7.dp))
                            Text(
                                text = "استعلام لحظه‌ای خریدار",
                                color = Color.White,
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }

                    // Tracking Code Chip
                    Surface(
                        shape = RoundedCornerShape(20.dp),
                        color = Color(0xFF1E293B),
                        border = BorderStroke(1.dp, Color(0xFF334155))
                    ) {
                        Text(
                            text = "کد: ${PersianFormatters.toPersianDigits(trackingCode)}",
                            color = Slate300,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Medium,
                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp)
                        )
                    }
                }

                Spacer(modifier = Modifier.height(20.dp))

                // Response Deadline Countdown Indicator (Warm Amber styling)
                Surface(
                    shape = RoundedCornerShape(16.dp),
                    color = if (isUrgent) TorobOutOfStockBackground else Color(0xFF1E293B),
                    border = BorderStroke(
                        1.dp,
                        if (isUrgent) TorobOutOfStockBorder else Color(0xFF334155)
                    )
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = Icons.Default.AccessTime,
                            contentDescription = null,
                            tint = if (isUrgent) TorobOutOfStockContent else TorobWarning,
                            modifier = Modifier.size(18.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = if (isUrgent) "فرصت فوری: ${PersianFormatters.formatRemainingTime(remainingSeconds)}" else "مهلت پاسخگویی: ${PersianFormatters.formatRemainingTime(remainingSeconds)}",
                            color = if (isUrgent) TorobOutOfStockContent else Slate100,
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // --- CENTER: Prominent Product Information Card ---
            Surface(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(24.dp),
                color = Color(0xFF1E293B),
                border = BorderStroke(1.2.dp, Color(0xFF334155)),
                shadowElevation = 8.dp
            ) {
                Column(
                    modifier = Modifier.padding(18.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.Top
                    ) {
                        // Product Image with graceful placeholder
                        Surface(
                            shape = RoundedCornerShape(16.dp),
                            color = Color(0xFF0F172A),
                            border = BorderStroke(1.dp, Color(0xFF334155)),
                            modifier = Modifier.size(86.dp)
                        ) {
                            if (!imageUrl.isNullOrBlank()) {
                                AsyncImage(
                                    model = ImageRequest.Builder(LocalContext.current)
                                        .data(imageUrl)
                                        .crossfade(true)
                                        .build(),
                                    contentDescription = productTitle,
                                    contentScale = ContentScale.Crop,
                                    modifier = Modifier.fillMaxSize()
                                )
                            } else {
                                Box(
                                    modifier = Modifier.fillMaxSize(),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.ShoppingBag,
                                        contentDescription = null,
                                        tint = Slate400,
                                        modifier = Modifier.size(38.dp)
                                    )
                                }
                            }
                        }

                        Spacer(modifier = Modifier.width(14.dp))

                        // Product Title & Metadata
                        Column(
                            modifier = Modifier.weight(1f),
                            verticalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            Text(
                                text = productTitle,
                                color = PureWhite,
                                fontSize = 15.sp,
                                fontWeight = FontWeight.Bold,
                                maxLines = 3,
                                overflow = TextOverflow.Ellipsis,
                                lineHeight = 22.sp
                            )

                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(4.dp)
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Person,
                                    contentDescription = null,
                                    tint = Slate400,
                                    modifier = Modifier.size(13.dp)
                                )
                                Text(
                                    text = customerName,
                                    color = Slate400,
                                    fontSize = 11.sp
                                )
                                Spacer(modifier = Modifier.width(6.dp))
                                Text(
                                    text = "• $categoryName",
                                    color = Slate500,
                                    fontSize = 11.sp
                                )
                            }
                        }
                    }

                    // Buyer note or request
                    if (buyerNote.isNotBlank()) {
                        Spacer(modifier = Modifier.height(14.dp))
                        Surface(
                            shape = RoundedCornerShape(12.dp),
                            color = Color(0xFF0F172A),
                            border = BorderStroke(1.dp, Color(0xFF334155)),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Row(
                                modifier = Modifier.padding(horizontal = 12.dp, vertical = 9.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(
                                    imageVector = Icons.Default.QuestionAnswer,
                                    contentDescription = null,
                                    tint = PrimaryBlueLight,
                                    modifier = Modifier.size(16.dp)
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(
                                    text = "«$buyerNote»",
                                    color = Slate200,
                                    fontSize = 11.sp,
                                    maxLines = 2,
                                    overflow = TextOverflow.Ellipsis
                                )
                            }
                        }
                    }

                    // Recorded / Reference Price
                    if (recordedPrice > 0) {
                        Spacer(modifier = Modifier.height(14.dp))
                        HorizontalDivider(color = Color(0xFF334155), thickness = 0.8.dp)
                        Spacer(modifier = Modifier.height(12.dp))

                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "آخرین قیمت ثبت‌شده در ترب:",
                                color = Slate400,
                                fontSize = 12.sp
                            )
                            Text(
                                text = PersianFormatters.formatPriceToman(recordedPrice),
                                color = Color(0xFF93C5FD),
                                fontSize = 15.sp,
                                fontWeight = FontWeight.Bold
                            )
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(20.dp))

            // --- BOTTOM ACTIONS: Primary, Quick Confirm, Out of Stock, Decline ---
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                // 1. Primary Action: "اعلام قیمت و موجودی" (Navigates to detail response screen)
                Button(
                    onClick = onAnswer,
                    enabled = !isSubmitting,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(54.dp),
                    shape = RoundedCornerShape(16.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = TorobRed,
                        contentColor = TorobSurface
                    ),
                    elevation = ButtonDefaults.buttonElevation(defaultElevation = 4.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.EditNote,
                        contentDescription = null,
                        modifier = Modifier.size(22.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "اعلام قیمت و موجودی",
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold
                    )
                    Spacer(modifier = Modifier.weight(1f))
                    Icon(
                        imageVector = Icons.Default.ChevronLeft,
                        contentDescription = null,
                        modifier = Modifier.size(20.dp)
                    )
                }

                // 2. Quick 1-Tap Confirmation for Recorded Price (if available)
                if (recordedPrice > 0) {
                    FilledTonalButton(
                        onClick = {
                            if (!isSubmitting) {
                                isSubmitting = true
                                onQuickConfirmPrice(recordedPrice)
                            }
                        },
                        enabled = !isSubmitting,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(48.dp),
                        shape = RoundedCornerShape(14.dp),
                        colors = ButtonDefaults.filledTonalButtonColors(
                            containerColor = Color(0xFF14532D),
                            contentColor = Color(0xFFDCFCE7)
                        ),
                        border = BorderStroke(1.dp, SuccessGreen.copy(alpha = 0.6f))
                    ) {
                        Icon(
                            imageVector = Icons.Default.Check,
                            contentDescription = null,
                            tint = Color(0xFFDCFCE7),
                            modifier = Modifier.size(18.dp)
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                        Text(
                            text = "تأیید سریع قیمت قبلی (${PersianFormatters.formatPriceToman(recordedPrice)})",
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }

                // 3. Secondary Actions Split: Out-of-Stock vs Decline (Two buttons side by side)
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    // Secondary Action 1: "اعلام عدم موجودی" (Warm Light Amber appearance)
                    Button(
                        onClick = {
                            if (!isSubmitting) {
                                isSubmitting = true
                                onOutOfStock()
                            }
                        },
                        enabled = !isSubmitting,
                        modifier = Modifier
                            .weight(1f)
                            .height(48.dp),
                        shape = RoundedCornerShape(14.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = TorobOutOfStockBackground,
                            contentColor = TorobOutOfStockContent
                        ),
                        border = BorderStroke(1.dp, TorobOutOfStockBorder)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Inventory,
                            contentDescription = null,
                            tint = TorobOutOfStockContent,
                            modifier = Modifier.size(17.dp)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = "اعلام عدم موجودی",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            color = TorobOutOfStockContent
                        )
                    }

                    // Secondary Action 2: "رد استعلام" (Neutral dark navy / slate appearance)
                    Button(
                        onClick = { showDeclineSheet = true },
                        enabled = !isSubmitting,
                        modifier = Modifier
                            .weight(1f)
                            .height(48.dp),
                        shape = RoundedCornerShape(14.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = TorobDeclineBackground,
                            contentColor = TorobDeclineContent
                        ),
                        border = BorderStroke(1.dp, TorobDeclineBorder)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Close,
                            contentDescription = null,
                            tint = TorobDeclineContent,
                            modifier = Modifier.size(17.dp)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = "رد استعلام",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            color = TorobDeclineContent
                        )
                    }
                }
            }
        }
    }

    // --- Material 3 Decline Reasons Modal Bottom Sheet ---
    if (showDeclineSheet) {
        ModalBottomSheet(
            onDismissRequest = {
                if (!isSubmitting) showDeclineSheet = false
            },
            containerColor = Color(0xFF0F172A),
            sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true),
            dragHandle = {
                Box(
                    modifier = Modifier
                        .padding(vertical = 10.dp)
                        .width(42.dp)
                        .height(4.dp)
                        .clip(CircleShape)
                        .background(Color(0xFF334155))
                )
            }
        ) {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 20.dp, vertical = 8.dp)
                    .imePadding()
                    .verticalScroll(rememberScrollState()),
                horizontalAlignment = Alignment.Start
            ) {
                Text(
                    text = "دلیل رد استعلام را انتخاب کنید",
                    fontSize = 17.sp,
                    fontWeight = FontWeight.Bold,
                    color = PureWhite
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "لطفاً دلیل عدم امکان پاسخگویی به این استعلام را مشخص فرمایید.",
                    fontSize = 12.sp,
                    color = Slate400
                )

                Spacer(modifier = Modifier.height(16.dp))

                // Predefined reasons list
                DeclineReason.values().forEach { reason ->
                    val isSelected = selectedDeclineReason == reason
                    Surface(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 4.dp)
                            .clip(RoundedCornerShape(12.dp))
                            .clickable { selectedDeclineReason = reason },
                        shape = RoundedCornerShape(12.dp),
                        color = if (isSelected) Color(0xFF1E293B) else Color.Transparent,
                        border = BorderStroke(
                            1.dp,
                            if (isSelected) TorobOutOfStockBorder else Color(0xFF334155)
                        )
                    ) {
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(horizontal = 12.dp, vertical = 10.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            RadioButton(
                                selected = isSelected,
                                onClick = { selectedDeclineReason = reason },
                                colors = RadioButtonDefaults.colors(
                                    selectedColor = TorobOutOfStockBorder,
                                    unselectedColor = Slate400
                                )
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Column {
                                Text(
                                    text = reason.title,
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = if (isSelected) TorobSurface else Slate200
                                )
                                Text(
                                    text = reason.description,
                                    fontSize = 11.sp,
                                    color = Slate400
                                )
                            }
                        }
                    }
                }

                // Special Handling: STORE_CLOSED -> Option to temporarily close store
                AnimatedVisibility(visible = selectedDeclineReason == DeclineReason.STORE_CLOSED) {
                    Column(modifier = Modifier.padding(top = 10.dp)) {
                        Surface(
                            shape = RoundedCornerShape(14.dp),
                            color = Color(0xFF1E293B),
                            border = BorderStroke(1.dp, TorobOutOfStockBorder.copy(alpha = 0.5f)),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clickable { closeShopOnDecline = !closeShopOnDecline }
                                    .padding(12.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Checkbox(
                                    checked = closeShopOnDecline,
                                    onCheckedChange = { closeShopOnDecline = it },
                                    colors = CheckboxDefaults.colors(
                                        checkedColor = TorobOutOfStockBorder,
                                        uncheckedColor = Slate400
                                    )
                                )
                                Spacer(modifier = Modifier.width(6.dp))
                                Column {
                                    Text(
                                        text = "تغییر وضعیت فروشگاه به تعطیل موقت",
                                        fontSize = 12.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = TorobSurface
                                    )
                                    Text(
                                        text = "با فعال‌سازی، فروشگاه موقتاً بسته شده و تا زمان بازگشایی مجدد استعلامی دریافت نخواهید کرد.",
                                        fontSize = 10.sp,
                                        color = Slate400,
                                        lineHeight = 15.sp
                                    )
                                }
                            }
                        }
                    }
                }

                // Custom Note Field if OTHER is selected
                AnimatedVisibility(visible = selectedDeclineReason == DeclineReason.OTHER) {
                    Column(modifier = Modifier.padding(top = 10.dp)) {
                        OutlinedTextField(
                            value = customDeclineNote,
                            onValueChange = { customDeclineNote = it },
                            placeholder = {
                                Text("توضیح کوتاه درباره دلیل رد استعلام...", fontSize = 12.sp, color = Slate400)
                            },
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(12.dp),
                            colors = OutlinedTextFieldDefaults.colors(
                                focusedBorderColor = TorobOutOfStockBorder,
                                unfocusedBorderColor = Color(0xFF334155),
                                focusedTextColor = TorobSurface,
                                unfocusedTextColor = Slate100
                            ),
                            maxLines = 3
                        )
                    }
                }

                Spacer(modifier = Modifier.height(18.dp))

                // Bottom Action Buttons in Sheet: Secondary (بازگشت) and Primary (تأیید و رد استعلام)
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(bottom = 16.dp),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    OutlinedButton(
                        onClick = { showDeclineSheet = false },
                        modifier = Modifier
                            .weight(1f)
                            .height(48.dp),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.outlinedButtonColors(contentColor = Slate300),
                        border = BorderStroke(1.dp, Color(0xFF334155))
                    ) {
                        Text("بازگشت", fontSize = 13.sp)
                    }

                    Button(
                        onClick = {
                            val reason = selectedDeclineReason ?: return@Button
                            if (!isSubmitting) {
                                isSubmitting = true
                                showDeclineSheet = false
                                onConfirmDecline(reason, customDeclineNote, closeShopOnDecline)
                            }
                        },
                        enabled = selectedDeclineReason != null && !isSubmitting,
                        modifier = Modifier
                            .weight(1.5f)
                            .height(48.dp),
                        shape = RoundedCornerShape(12.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color(0xFF334155),
                            contentColor = Color.White,
                            disabledContainerColor = Color(0xFF1E293B),
                            disabledContentColor = Slate500
                        ),
                        border = BorderStroke(
                            1.dp,
                            if (selectedDeclineReason != null) TorobDeclineBorder else Color.Transparent
                        )
                    ) {
                        Text(
                            text = "تأیید و رد استعلام",
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }
        }
    }
}

// Backward-compatibility alias
@Composable
fun IncomingCallScreen(
    inquiryId: String,
    onAnswer: () -> Unit,
    onDecline: () -> Unit
) {
    SmartInquiryCallScreen(
        inquiryId = inquiryId,
        fallbackTitle = "استعلام جدید خریدار",
        fallbackBody = "خریدار منتظر پاسخ قیمت و موجودی شماست",
        onAnswer = onAnswer,
        onQuickConfirmPrice = { onAnswer() },
        onOutOfStock = onDecline,
        onConfirmDecline = { _, _, _ -> onDecline() },
        onDismiss = onDecline
    )
}

