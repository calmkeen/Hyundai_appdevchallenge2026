package com.carcue.app

import android.content.Context
import android.graphics.SurfaceTexture
import android.opengl.EGL14
import android.opengl.EGLConfig
import android.opengl.EGLContext
import android.opengl.EGLDisplay
import android.opengl.EGLSurface
import android.opengl.GLES20.*
import android.opengl.Matrix
import android.os.SystemClock
import android.view.Choreographer
import android.view.MotionEvent
import android.view.TextureView
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.FloatBuffer
import kotlin.math.*

/** A real depth-tested OpenGL scene embedded in Compose, with an articulated mesh.
 * TextureView participates in ordinary clipping, screenshots and scrolling.
 * EGL, updates and drawing all belong to the UI thread; no orphan render thread.
 */
class ArticulatedVehicleView(context: Context) : TextureView(context), TextureView.SurfaceTextureListener,
    Choreographer.FrameCallback {
    private var display: EGLDisplay = EGL14.EGL_NO_DISPLAY
    private var eglContext: EGLContext = EGL14.EGL_NO_CONTEXT
    private var surface: EGLSurface = EGL14.EGL_NO_SURFACE
    private var program = 0
    private val counts: IntArray
    private val vertices: Array<FloatBuffer>
    private val hinge = FloatArray(3)
    private var state = "unknown"
    private var doorAngle = 22f
    private var fromAngle = 22f
    private var targetAngle = 22f
    private var changedAt = 0L
    private var callbackPending = false
    private var yaw = 48f
    private var pitch = 21f
    private var touchX = 0f
    private var touchY = 0f
    var interactive = true
    // Read by instrumentation to verify rendering and actual animated pose.
    var renderedFrames = 0L; private set
    val renderedDoorAngle: Float get() = doorAngle
    val renderedYaw: Float get() = yaw
    private val model = FloatArray(16)
    private val view = FloatArray(16)
    private val projection = FloatArray(16)
    private val vp = FloatArray(16)
    private val mvp = FloatArray(16)
    private val eye = FloatArray(3)

    init {
        surfaceTextureListener = this
        isOpaque = true
        val data = context.assets.open("models/ioniq5-articulated.ccmesh").use { it.readBytes() }
        val bytes = ByteBuffer.wrap(data).order(ByteOrder.LITTLE_ENDIAN)
        check(bytes.int == 0x324D4343) { "Invalid CarCue mesh" }
        counts = IntArray(4) { bytes.int }
        repeat(3) { hinge[it] = bytes.float }
        check(counts.all { it > 0 && it % 3 == 0 } && data.size == 32 + counts.sum()*48)
        vertices = Array(4) { i ->
            ByteBuffer.allocateDirect(counts[i]*48).order(ByteOrder.nativeOrder()).asFloatBuffer().also { buffer ->
                repeat(counts[i]*12) { buffer.put(bytes.float) }; buffer.position(0)
            }
        }
    }

    fun setDoorState(next: String) {
        if (state == next) return
        state = next
        fromAngle = doorAngle
        targetAngle = when (next) { "open" -> 62f; "closed" -> 0f; else -> 22f }
        changedAt = SystemClock.uptimeMillis()
        schedule()
    }

    private fun schedule() {
        if (surface != EGL14.EGL_NO_SURFACE && !callbackPending) {
            callbackPending = true
            Choreographer.getInstance().postFrameCallback(this)
        }
    }

    override fun onSurfaceTextureAvailable(texture: SurfaceTexture, width: Int, height: Int) {
        display = EGL14.eglGetDisplay(EGL14.EGL_DEFAULT_DISPLAY)
        val version = IntArray(2)
        check(EGL14.eglInitialize(display, version, 0, version, 1))
        val configs = arrayOfNulls<EGLConfig>(1); val n = IntArray(1)
        fun choose(samples: Int): Boolean = EGL14.eglChooseConfig(display,
            intArrayOf(EGL14.EGL_RENDERABLE_TYPE, EGL14.EGL_OPENGL_ES2_BIT,
                EGL14.EGL_RED_SIZE, 8, EGL14.EGL_GREEN_SIZE, 8, EGL14.EGL_BLUE_SIZE, 8,
                EGL14.EGL_DEPTH_SIZE, 24, EGL14.EGL_SURFACE_TYPE, EGL14.EGL_WINDOW_BIT,
                EGL14.EGL_SAMPLE_BUFFERS, if (samples>0) 1 else 0, EGL14.EGL_SAMPLES, samples, EGL14.EGL_NONE),
            0, configs, 0, 1, n, 0) && n[0]>0
        check(choose(4) || choose(0))
        eglContext = EGL14.eglCreateContext(display, configs[0], EGL14.EGL_NO_CONTEXT,
            intArrayOf(EGL14.EGL_CONTEXT_CLIENT_VERSION, 2, EGL14.EGL_NONE), 0)
        surface = EGL14.eglCreateWindowSurface(display, configs[0], texture, intArrayOf(EGL14.EGL_NONE), 0)
        check(EGL14.eglMakeCurrent(display, surface, surface, eglContext))
        fun shader(type: Int, source: String): Int = glCreateShader(type).also { id ->
            glShaderSource(id, source); glCompileShader(id)
            val status = IntArray(1); glGetShaderiv(id, GL_COMPILE_STATUS, status, 0)
            check(status[0] == GL_TRUE) { glGetShaderInfoLog(id) }
        }
        val vs = shader(GL_VERTEX_SHADER, VERTEX)
        val fs = shader(GL_FRAGMENT_SHADER, FRAGMENT)
        program = glCreateProgram()
        glAttachShader(program, vs); glAttachShader(program, fs); glLinkProgram(program)
        val status = IntArray(1); glGetProgramiv(program, GL_LINK_STATUS, status, 0)
        check(status[0] == GL_TRUE) { glGetProgramInfoLog(program) }
        glDeleteShader(vs); glDeleteShader(fs)
        glEnable(GL_DEPTH_TEST); glDisable(GL_CULL_FACE)
        schedule()
    }

    override fun onSurfaceTextureSizeChanged(texture: SurfaceTexture, width: Int, height: Int) { schedule() }
    override fun onSurfaceTextureUpdated(texture: SurfaceTexture) = Unit
    override fun onSurfaceTextureDestroyed(texture: SurfaceTexture): Boolean {
        releaseScene(); return true
    }

    fun releaseScene() {
        Choreographer.getInstance().removeFrameCallback(this); callbackPending = false
        if (display != EGL14.EGL_NO_DISPLAY) {
            if (program != 0) glDeleteProgram(program)
            EGL14.eglMakeCurrent(display, EGL14.EGL_NO_SURFACE, EGL14.EGL_NO_SURFACE, EGL14.EGL_NO_CONTEXT)
            EGL14.eglDestroySurface(display, surface)
            EGL14.eglDestroyContext(display, eglContext)
            EGL14.eglTerminate(display)
        }
        program = 0; surface = EGL14.EGL_NO_SURFACE
        eglContext = EGL14.EGL_NO_CONTEXT; display = EGL14.EGL_NO_DISPLAY
    }

    override fun doFrame(frameTimeNanos: Long) {
        callbackPending = false
        if (surface == EGL14.EGL_NO_SURFACE || width == 0 || height == 0) return
        check(EGL14.eglMakeCurrent(display, surface, surface, eglContext))
        val t = ((SystemClock.uptimeMillis()-changedAt)/720f).coerceIn(0f,1f)
        val ease = t*t*(3f-2f*t)
        doorAngle = fromAngle + (targetAngle-fromAngle)*ease
        glViewport(0,0,width,height)
        glClearColor(244/255f,247/255f,252/255f,1f)
        glClear(GL_COLOR_BUFFER_BIT or GL_DEPTH_BUFFER_BIT)
        val aspect = width.toFloat()/height
        val distance = max(6.6f, 4.5f/aspect) * (1f + (pitch-21f).coerceAtLeast(0f)*.018f)
        val a = Math.toRadians(yaw.toDouble()); val b = Math.toRadians(pitch.toDouble())
        eye[0]=(-sin(a)*cos(b)*distance).toFloat()
        eye[1]=(sin(b)*distance).toFloat()+.70f
        eye[2]=(-cos(a)*cos(b)*distance).toFloat()
        Matrix.setLookAtM(view,0,eye[0],eye[1],eye[2],0f,.70f,0f,0f,1f,0f)
        Matrix.perspectiveM(projection,0,31f,aspect,.1f,35f)
        Matrix.multiplyMM(vp,0,projection,0,view,0)
        glUseProgram(program)
        glUniform3fv(glGetUniformLocation(program,"uEye"),1,eye,0)
        for (i in 0..3) {
            if (i == 2) { glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA); glDepthMask(false) }
            Matrix.setIdentityM(model,0)
            if (i%2==1) {
                Matrix.translateM(model,0,hinge[0],hinge[1],hinge[2])
                Matrix.rotateM(model,0,-doorAngle,0f,1f,0f)
            }
            Matrix.multiplyMM(mvp,0,vp,0,model,0)
            glUniformMatrix4fv(glGetUniformLocation(program,"uMvp"),1,false,mvp,0)
            glUniformMatrix4fv(glGetUniformLocation(program,"uModel"),1,false,model,0)
            glUniform1f(glGetUniformLocation(program,"uUnknown"),if (i%2==1 && state=="unknown") 1f else 0f)
            for ((name, offset, size) in listOf(Triple("aPosition",0,3),Triple("aNormal",3,3),Triple("aColour",6,3),Triple("aSurface",9,3))) {
                val location=glGetAttribLocation(program,name)
                vertices[i].position(offset)
                glEnableVertexAttribArray(location)
                glVertexAttribPointer(location,size,GL_FLOAT,false,48,vertices[i])
            }
            glDrawArrays(GL_TRIANGLES,0,counts[i])
        }
        glDepthMask(true); glDisable(GL_BLEND)
        check(glGetError()==GL_NO_ERROR) { "CarCue OpenGL render error" }
        check(EGL14.eglSwapBuffers(display,surface))
        renderedFrames++
        if (t<1f) schedule()
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (!interactive) return false
        when(event.actionMasked) {
            MotionEvent.ACTION_DOWN -> { touchX=event.x; touchY=event.y; parent.requestDisallowInterceptTouchEvent(true); return true }
            MotionEvent.ACTION_MOVE -> {
                yaw=(yaw-(event.x-touchX)*.30f)%360f
                pitch=(pitch+(event.y-touchY)*.15f).coerceIn(7f,48f)
                touchX=event.x; touchY=event.y; schedule(); return true
            }
            MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> { parent.requestDisallowInterceptTouchEvent(false); performClick(); return true }
        }
        return true
    }
    override fun performClick(): Boolean { super.performClick(); return true }

    companion object {
        private const val VERTEX = """
            uniform mat4 uMvp; uniform mat4 uModel;
            attribute vec3 aPosition; attribute vec3 aNormal; attribute vec3 aColour; attribute vec3 aSurface;
            varying vec3 vPosition; varying vec3 vNormal; varying vec3 vColour; varying vec3 vSurface;
            void main() { vPosition=(uModel*vec4(aPosition,1.0)).xyz;
                vNormal=mat3(uModel)*aNormal; vColour=aColour; vSurface=aSurface;
                gl_Position=uMvp*vec4(aPosition,1.0); }
        """
        // Smooth imported normals and metallic/roughness BRDF under a procedural
        // studio sky. No downloaded HDRI, raster car image or external viewer.
        private const val FRAGMENT = """
            precision mediump float;
            uniform vec3 uEye; uniform float uUnknown;
            varying vec3 vPosition; varying vec3 vNormal; varying vec3 vColour; varying vec3 vSurface;
            const float PI=3.14159265;
            vec3 fresnel(float cosine, vec3 f0) { return f0+(1.0-f0)*pow(1.0-cosine,5.0); }
            vec3 sky(vec3 r, float rough) {
                vec3 c=mix(vec3(0.20,0.23,0.28),vec3(0.85,0.91,1.0),smoothstep(-0.35,0.75,r.y));
                float strip=pow(max(dot(r,normalize(vec3(-0.5,1.0,-0.8))),0.0),mix(28.0,4.0,rough));
                c+=vec3(1.5)*strip;
                return mix(c,vec3(0.65,0.70,0.76),rough*0.45);
            }
            vec3 lamp(vec3 n,vec3 v,vec3 l,vec3 base,vec3 f0,float rough,float metal,vec3 radiance) {
                vec3 h=normalize(v+l);
                float nv=max(dot(n,v),0.001); float nl=max(dot(n,l),0.0);
                float nh=max(dot(n,h),0.0); float vh=max(dot(v,h),0.0);
                float a=rough*rough; float aa=a*a;
                float den=nh*nh*(aa-1.0)+1.0;
                float d=aa/max(PI*den*den,0.0001);
                float k=(rough+1.0)*(rough+1.0)/8.0;
                float g=(nv/(nv*(1.0-k)+k))*(nl/(nl*(1.0-k)+k));
                vec3 f=fresnel(vh,f0);
                vec3 spec=d*g*f/max(4.0*nv*nl,0.001);
                vec3 diffuse=(1.0-f)*(1.0-metal)*base/PI;
                return (diffuse+spec)*radiance*nl;
            }
            void main() {
                if(vSurface.x<0.0) { gl_FragColor=vec4(vColour,1.0); return; }
                vec3 n=normalize(vNormal); if(!gl_FrontFacing) n=-n;
                vec3 v=normalize(uEye-vPosition);
                float rough=clamp(vSurface.x,0.12,1.0); float metal=clamp(vSurface.y,0.0,1.0);
                float alpha=vSurface.z; vec3 base=vColour;
                if(uUnknown>0.5) { base=mix(base,vec3(0.33,0.38,0.44),0.65); rough=max(rough,0.65); }
                vec3 f0=mix(vec3(0.04),base,metal);
                vec3 c=base*(1.0-metal)*(0.16+0.18*max(n.y,0.0));
                c+=sky(reflect(-v,n),rough)*fresnel(max(dot(n,v),0.0),f0)*(0.7-rough*0.25);
                c+=lamp(n,v,normalize(vec3(-3.0,6.0,-4.0)),base,f0,rough,metal,vec3(3.2,3.3,3.5));
                c+=lamp(n,v,normalize(vec3(4.0,2.5,2.0)),base,f0,rough,metal,vec3(1.2,1.3,1.5));
                if(alpha<0.99) {
                    c+=vec3(0.015,0.025,0.033);
                    alpha=clamp(alpha+pow(1.0-max(dot(n,v),0.0),4.0)*0.35,0.0,0.85);
                }
                c=clamp((c*(2.51*c+0.03))/(c*(2.43*c+0.59)+0.14),0.0,1.0);
                gl_FragColor=vec4(pow(c,vec3(1.0/2.2)),alpha);
            }
        """
    }
}
