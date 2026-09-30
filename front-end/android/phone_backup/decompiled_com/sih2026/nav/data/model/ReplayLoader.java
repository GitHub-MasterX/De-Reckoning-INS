package com.sih2026.nav.data.model;

import android.content.Context;
import androidx.autofill.HintConstants;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.Reader;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;
import kotlin.Metadata;
import kotlin.collections.CollectionsKt;
import kotlin.collections.IntIterator;
import kotlin.io.CloseableKt;
import kotlin.io.TextStreamsKt;
import kotlin.jvm.internal.Intrinsics;
import kotlin.ranges.IntRange;
import kotlin.ranges.RangesKt;
import kotlin.text.Charsets;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/* JADX INFO: compiled from: ReplayClip.kt */
/* JADX INFO: loaded from: classes9.dex */
@Metadata(d1 = {"\u0000J\n\u0002\u0018\u0002\n\u0002\u0010\u0000\n\u0002\b\u0002\n\u0002\u0010\u000e\n\u0000\n\u0002\u0010\u0018\n\u0000\n\u0002\u0018\u0002\n\u0000\n\u0002\u0010\u0013\n\u0000\n\u0002\u0010\u0014\n\u0000\n\u0002\u0010 \n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0002\n\u0002\u0018\u0002\n\u0000\n\u0002\u0018\u0002\n\u0002\b\u0004\bÇ\u0002\u0018\u00002\u00020\u0001B\u0007\b\u0002¢\u0006\u0002\u0010\u0002J\u0010\u0010\u0005\u001a\u00020\u00062\u0006\u0010\u0007\u001a\u00020\bH\u0002J\u0010\u0010\t\u001a\u00020\n2\u0006\u0010\u0007\u001a\u00020\bH\u0002J\u0010\u0010\u000b\u001a\u00020\f2\u0006\u0010\u0007\u001a\u00020\bH\u0002J\u0014\u0010\r\u001a\b\u0012\u0004\u0012\u00020\u000f0\u000e2\u0006\u0010\u0010\u001a\u00020\u0011J\u0010\u0010\u0012\u001a\u00020\u000f2\u0006\u0010\u0013\u001a\u00020\u0014H\u0002J\u0016\u0010\u0015\u001a\u00020\u00162\u0006\u0010\u0010\u001a\u00020\u00112\u0006\u0010\u0017\u001a\u00020\u0004J\u0018\u0010\u0018\u001a\u00020\u00042\u0006\u0010\u0010\u001a\u00020\u00112\u0006\u0010\u0019\u001a\u00020\u0004H\u0002R\u000e\u0010\u0003\u001a\u00020\u0004X\u0082T¢\u0006\u0002\n\u0000¨\u0006\u001a"}, d2 = {"Lcom/sih2026/nav/data/model/ReplayLoader;", "", "()V", "DIR", "", "booleans", "", "a", "Lorg/json/JSONArray;", "doubles", "", "floats", "", "index", "", "Lcom/sih2026/nav/data/model/ClipInfo;", "context", "Landroid/content/Context;", "info", "o", "Lorg/json/JSONObject;", "load", "Lcom/sih2026/nav/data/model/ReplayClip;", "id", "read", HintConstants.AUTOFILL_HINT_NAME, "app_debug"}, k = 1, mv = {1, 9, 0}, xi = 48)
public final class ReplayLoader {
    public static final int $stable = 0;
    private static final String DIR = "replay";
    public static final ReplayLoader INSTANCE = new ReplayLoader();

    private ReplayLoader() {
    }

    private final boolean[] booleans(JSONArray a) {
        int length = a.length();
        boolean[] zArr = new boolean[length];
        for (int i = 0; i < length; i++) {
            zArr[i] = a.getBoolean(i);
        }
        return zArr;
    }

    private final double[] doubles(JSONArray a) {
        int length = a.length();
        double[] dArr = new double[length];
        for (int i = 0; i < length; i++) {
            dArr[i] = a.getDouble(i);
        }
        return dArr;
    }

    private final float[] floats(JSONArray a) {
        int length = a.length();
        float[] fArr = new float[length];
        for (int i = 0; i < length; i++) {
            fArr[i] = (float) a.getDouble(i);
        }
        return fArr;
    }

    private final ClipInfo info(JSONObject o) throws JSONException {
        String string = o.getString("id");
        Intrinsics.checkNotNullExpressionValue(string, "getString(...)");
        String string2 = o.getString("driver");
        Intrinsics.checkNotNullExpressionValue(string2, "getString(...)");
        String string3 = o.getString("role");
        Intrinsics.checkNotNullExpressionValue(string3, "getString(...)");
        String string4 = o.getString("drive");
        Intrinsics.checkNotNullExpressionValue(string4, "getString(...)");
        int i = o.getInt("session");
        String string5 = o.getString("band");
        Intrinsics.checkNotNullExpressionValue(string5, "getString(...)");
        return new ClipInfo(string, string2, string3, string4, i, string5, o.getInt("turns"), o.getDouble("avg_kmh"), o.getDouble("distance_m"), o.getDouble("duration_s"), o.getDouble("final_drift_m"), o.getDouble("final_drift_pct"), o.getDouble("final_base_m"), o.getDouble("final_base_pct"));
    }

    private final String read(Context context, String name) throws IOException {
        InputStream inputStreamOpen = context.getAssets().open("replay/" + name);
        Intrinsics.checkNotNullExpressionValue(inputStreamOpen, "open(...)");
        Reader inputStreamReader = new InputStreamReader(inputStreamOpen, Charsets.UTF_8);
        BufferedReader bufferedReader = inputStreamReader instanceof BufferedReader ? (BufferedReader) inputStreamReader : new BufferedReader(inputStreamReader, 8192);
        try {
            String text = TextStreamsKt.readText(bufferedReader);
            CloseableKt.closeFinally(bufferedReader, null);
            return text;
        } catch (Throwable th) {
            try {
                throw th;
            } catch (Throwable th2) {
                CloseableKt.closeFinally(bufferedReader, th);
                throw th2;
            }
        }
    }

    public final List<ClipInfo> index(Context context) throws JSONException {
        Intrinsics.checkNotNullParameter(context, "context");
        JSONArray jSONArray = new JSONObject(read(context, "index.json")).getJSONArray("clips");
        IntRange intRangeUntil = RangesKt.until(0, jSONArray.length());
        ArrayList arrayList = new ArrayList(CollectionsKt.collectionSizeOrDefault(intRangeUntil, 10));
        Iterator<Integer> it = intRangeUntil.iterator();
        while (it.hasNext()) {
            int iNextInt = ((IntIterator) it).nextInt();
            ReplayLoader replayLoader = INSTANCE;
            JSONObject jSONObject = jSONArray.getJSONObject(iNextInt);
            Intrinsics.checkNotNullExpressionValue(jSONObject, "getJSONObject(...)");
            arrayList.add(replayLoader.info(jSONObject));
        }
        return arrayList;
    }

    public final ReplayClip load(Context context, String id) throws JSONException {
        Intrinsics.checkNotNullParameter(context, "context");
        Intrinsics.checkNotNullParameter(id, "id");
        JSONObject jSONObject = new JSONObject(read(context, id + ".json"));
        JSONObject jSONObject2 = jSONObject.getJSONObject("lead_in");
        ClipInfo clipInfoInfo = info(jSONObject);
        int i = jSONObject.getInt("hz");
        double d = jSONObject.getDouble("engine_speed_kmh");
        JSONArray jSONArray = jSONObject2.getJSONArray("lat");
        Intrinsics.checkNotNullExpressionValue(jSONArray, "getJSONArray(...)");
        double[] dArrDoubles = doubles(jSONArray);
        JSONArray jSONArray2 = jSONObject2.getJSONArray("lon");
        Intrinsics.checkNotNullExpressionValue(jSONArray2, "getJSONArray(...)");
        double[] dArrDoubles2 = doubles(jSONArray2);
        JSONArray jSONArray3 = jSONObject2.getJSONArray("heading");
        Intrinsics.checkNotNullExpressionValue(jSONArray3, "getJSONArray(...)");
        float[] fArrFloats = floats(jSONArray3);
        JSONArray jSONArray4 = jSONObject2.getJSONArray("speed_kmh");
        Intrinsics.checkNotNullExpressionValue(jSONArray4, "getJSONArray(...)");
        float[] fArrFloats2 = floats(jSONArray4);
        JSONArray jSONArray5 = jSONObject.getJSONArray("true_lat");
        Intrinsics.checkNotNullExpressionValue(jSONArray5, "getJSONArray(...)");
        double[] dArrDoubles3 = doubles(jSONArray5);
        JSONArray jSONArray6 = jSONObject.getJSONArray("true_lon");
        Intrinsics.checkNotNullExpressionValue(jSONArray6, "getJSONArray(...)");
        double[] dArrDoubles4 = doubles(jSONArray6);
        JSONArray jSONArray7 = jSONObject.getJSONArray("true_heading");
        Intrinsics.checkNotNullExpressionValue(jSONArray7, "getJSONArray(...)");
        float[] fArrFloats3 = floats(jSONArray7);
        JSONArray jSONArray8 = jSONObject.getJSONArray("true_speed_kmh");
        Intrinsics.checkNotNullExpressionValue(jSONArray8, "getJSONArray(...)");
        float[] fArrFloats4 = floats(jSONArray8);
        JSONArray jSONArray9 = jSONObject.getJSONArray("true_dist_m");
        Intrinsics.checkNotNullExpressionValue(jSONArray9, "getJSONArray(...)");
        float[] fArrFloats5 = floats(jSONArray9);
        JSONArray jSONArray10 = jSONObject.getJSONArray("pf_lat");
        Intrinsics.checkNotNullExpressionValue(jSONArray10, "getJSONArray(...)");
        double[] dArrDoubles5 = doubles(jSONArray10);
        JSONArray jSONArray11 = jSONObject.getJSONArray("pf_lon");
        Intrinsics.checkNotNullExpressionValue(jSONArray11, "getJSONArray(...)");
        double[] dArrDoubles6 = doubles(jSONArray11);
        JSONArray jSONArray12 = jSONObject.getJSONArray("pf_heading");
        Intrinsics.checkNotNullExpressionValue(jSONArray12, "getJSONArray(...)");
        float[] fArrFloats6 = floats(jSONArray12);
        JSONArray jSONArray13 = jSONObject.getJSONArray("pf_on_map");
        Intrinsics.checkNotNullExpressionValue(jSONArray13, "getJSONArray(...)");
        boolean[] zArrBooleans = booleans(jSONArray13);
        JSONArray jSONArray14 = jSONObject.getJSONArray("nomap_lat");
        Intrinsics.checkNotNullExpressionValue(jSONArray14, "getJSONArray(...)");
        double[] dArrDoubles7 = doubles(jSONArray14);
        JSONArray jSONArray15 = jSONObject.getJSONArray("nomap_lon");
        Intrinsics.checkNotNullExpressionValue(jSONArray15, "getJSONArray(...)");
        double[] dArrDoubles8 = doubles(jSONArray15);
        JSONArray jSONArray16 = jSONObject.getJSONArray("drift_m");
        Intrinsics.checkNotNullExpressionValue(jSONArray16, "getJSONArray(...)");
        float[] fArrFloats7 = floats(jSONArray16);
        JSONArray jSONArray17 = jSONObject.getJSONArray("drift_pct");
        Intrinsics.checkNotNullExpressionValue(jSONArray17, "getJSONArray(...)");
        float[] fArrFloats8 = floats(jSONArray17);
        JSONArray jSONArray18 = jSONObject.getJSONArray("nomap_drift_m");
        Intrinsics.checkNotNullExpressionValue(jSONArray18, "getJSONArray(...)");
        float[] fArrFloats9 = floats(jSONArray18);
        JSONArray jSONArray19 = jSONObject.getJSONArray("nomap_drift_pct");
        Intrinsics.checkNotNullExpressionValue(jSONArray19, "getJSONArray(...)");
        return new ReplayClip(clipInfoInfo, i, d, dArrDoubles, dArrDoubles2, fArrFloats, fArrFloats2, dArrDoubles3, dArrDoubles4, fArrFloats3, fArrFloats4, fArrFloats5, dArrDoubles5, dArrDoubles6, fArrFloats6, zArrBooleans, dArrDoubles7, dArrDoubles8, fArrFloats7, fArrFloats8, fArrFloats9, floats(jSONArray19));
    }
}
