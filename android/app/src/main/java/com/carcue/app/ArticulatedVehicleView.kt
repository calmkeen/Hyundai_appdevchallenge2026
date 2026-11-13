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
        check(bytes.int == 0x314D4343) { "Invalid CarCue mesh" }
        counts = intArrayOf(bytes.int, bytes.int)
        check(counts.all { it > 0 && it % 3 == 0 } && data.size == 12 + counts.sum()*40)
        vertices = Array(2) { i ->
            ByteBuffer.allocateDirect(counts[i]*40).order(ByteOrder.nativeOrder()).asFloatBuffer().also { buffer ->
                repeat(counts[i]*10) { buffer.put(bytes.float) }; buffer.position(0)
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
        for (i in 0..1) {
            Matrix.setIdentityM(model,0)
            if (i==1) {
                Matrix.translateM(model,0,-.932f,0f,-1.12f)
                Matrix.rotateM(model,0,-doorAngle,0f,1f,0f)
            }
            Matrix.multiplyMM(mvp,0,vp,0,model,0)
            glUniformMatrix4fv(glGetUniformLocation(program,"uMvp"),1,false,mvp,0)
            glUniformMatrix4fv(glGetUniformLocation(program,"uModel"),1,false,model,0)
            glUniform1f(glGetUniformLocation(program,"uUnknown"),if (i==1 && state=="unknown") 1f else 0f)
            for ((name, offset, size) in listOf(Triple("aPosition",0,3),Triple("aNormal",3,3),Triple("aColour",6,4))) {
                val location=glGetAttribLocation(program,name)
                vertices[i].position(offset)
                glEnableVertexAttribArray(location)
                glVertexAttribPointer(location,size,GL_FLOAT,false,40,vertices[i])
            }
            glDrawArrays(GL_TRIANGLES,0,counts[i])
        }
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
            attribute vec3 aPosition; attribute vec3 aNormal; attribute vec4 aColour;
            varying vec3 vPosition; varying vec3 vNormal; varying vec4 vColour;
            void main() { vPosition=(uModel*vec4(aPosition,1.0)).xyz;
                vNormal=mat3(uModel)*aNormal; vColour=aColour;
                gl_Position=uMvp*vec4(aPosition,1.0); }
        """
        private const val FRAGMENT = """
            precision mediump float;
            uniform vec3 uEye; uniform float uUnknown;
            varying vec3 vPosition; varying vec3 vNormal; varying vec4 vColour;
            void main() {
                if(vColour.a<0.0) {gl_FragColor=vec4(vColour.rgb,1.0); return;}
                vec3 n=normalize(vNormal); if(!gl_FrontFacing) n=-n;
                vec3 v=normalize(uEye-vPosition);
                vec3 key=normalize(vec3(-3.0,6.0,-4.0));
                float diffuse=max(dot(n,key),0.0);
                float fill=max(dot(n,normalize(vec3(4.0,3.0,2.0))),0.0);
                float spec=pow(max(dot(n,normalize(key+v)),0.0),48.0)*vColour.a;
                float fresnel=pow(1.0-max(dot(n,v),0.0),3.0)*vColour.a;
                vec3 c=vColour.rgb*(0.48+diffuse*0.42+fill*0.16)+vec3(spec*.42+fresnel*.13);
                if(uUnknown>0.5) c=mix(c,vec3(0.63,0.67,0.72),0.55);
                gl_FragColor=vec4(c,1.0);
            }
        """
    }
}
