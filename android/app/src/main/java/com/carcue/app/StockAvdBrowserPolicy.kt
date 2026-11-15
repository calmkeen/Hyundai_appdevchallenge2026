package com.carcue.app

/** Environment gate only; the opener must also validate the installed system handler. */
internal fun stockAvdBrowserAllowed(debug: Boolean, submissionAvd: Boolean, mock: Boolean, api: Int, hardware: String): Boolean =
    (debug || submissionAvd) && !mock && api == 34 && hardware == "ranchu"
