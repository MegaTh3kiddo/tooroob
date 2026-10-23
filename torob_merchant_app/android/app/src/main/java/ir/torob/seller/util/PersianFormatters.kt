package ir.torob.seller.util

import java.text.DecimalFormat

object PersianFormatters {
    private val persianDigits = arrayOf('۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹')

    fun toPersianDigits(text: String?): String {
        if (text == null) return ""
        val builder = StringBuilder()
        for (char in text) {
            if (char in '0'..'9') {
                builder.append(persianDigits[char - '0'])
            } else {
                builder.append(char)
            }
        }
        return builder.toString()
    }

    fun toPersianDigits(number: Long): String {
        return toPersianDigits(number.toString())
    }

    fun toPersianDigits(number: Int): String {
        return toPersianDigits(number.toString())
    }

    fun formatPriceToman(amount: Long): String {
        val formatter = DecimalFormat("#,###")
        val formatted = formatter.format(amount)
        return "${toPersianDigits(formatted)} تومان"
    }

    fun formatRemainingTime(seconds: Long): String {
        if (seconds <= 0) return "منقضی شده"
        val mins = seconds / 60
        val secs = seconds % 60
        val secStr = if (secs < 10) "0$secs" else secs.toString()
        return "${toPersianDigits(mins)}:${toPersianDigits(secStr)}"
    }
}
