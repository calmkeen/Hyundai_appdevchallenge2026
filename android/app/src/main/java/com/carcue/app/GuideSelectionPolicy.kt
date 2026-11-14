package com.carcue.app

/** Reconcile only the selected original's scope; changing UI language does not withdraw that original. */
internal object GuideSelectionPolicy {
    fun reconcile(selected: Guide?, profile: Profile, locale: String, snapshot: List<Guide>): Guide? {
        if (selected == null || !selected.publicationVerified || selected.locale != locale) return selected
        if (profile.id !in selected.profileIds || selected.manualSetId != profile.manualSetId ||
            selected.sourceVersion != profile.manualVersion) return null
        return snapshot.singleOrNull { it.publicationVerified && it.id == selected.id && it.locale == locale &&
            profile.id in it.profileIds && it.manualSetId == profile.manualSetId && it.sourceVersion == profile.manualVersion }
    }
}
