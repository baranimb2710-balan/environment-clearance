"""
Landing page module for VYRO - AI-powered Environmental Clearance Review.
Pure Streamlit component incorporating an auto-rotating hero carousel via st.components.v1.html.
"""
import streamlit as st
import streamlit.components.v1 as components


def render_landing_page():
    """Renders the VYRO landing page with hero carousel and Get Started action."""
    
    # 1. Branding: Website name VYRO & Tagline
    st.markdown(
        """
        <div style="text-align: center; margin-top: 10px; margin-bottom: 25px;">
            <h1 style="font-size: 3.8rem; font-weight: 900; letter-spacing: 4px; margin: 0; 
                       background: linear-gradient(135deg, #4ade80 0%, #22c55e 50%, #16a34a 100%);
                       -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
                VYRO
            </h1>
            <p style="font-size: 1.25rem; font-weight: 500; color: #94a3b8; margin-top: 8px; letter-spacing: 1px;">
                AI-powered Environmental Clearance Review
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 2. Hero Carousel HTML/CSS/JS Component
    carousel_html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <style>
            * {
                box-sizing: border-box;
                margin: 0;
                padding: 0;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            }
            body {
                background: transparent;
                display: flex;
                justify-content: center;
                align-items: center;
                width: 100%;
                overflow: hidden;
            }
            .carousel-container {
                position: relative;
                width: 100%;
                max-width: 1100px;
                height: 440px;
                border-radius: 20px;
                overflow: hidden;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
                border: 1px solid rgba(255, 255, 255, 0.12);
                background: #0f172a;
            }
            .slide {
                position: absolute;
                inset: 0;
                opacity: 0;
                transition: opacity 0.8s ease-in-out, transform 0.8s ease-in-out;
                transform: scale(1.03);
                background-size: cover;
                background-position: center;
                display: flex;
                align-items: flex-end;
                pointer-events: none;
            }
            .slide.active {
                opacity: 1;
                transform: scale(1);
                pointer-events: auto;
            }
            /* Slide 1 - Forest fire */
            .slide-1 {
                background-color: #2b110a;
                background-image: 
                    linear-gradient(180deg, rgba(15, 23, 42, 0.35) 0%, rgba(20, 10, 10, 0.75) 60%, rgba(10, 5, 5, 0.92) 100%),
                    url('https://images.unsplash.com/photo-1542385151-efd9000785a0?auto=format&fit=crop&w=1600&q=80');
            }
            /* Slide 2 - Industrial smoke */
            .slide-2 {
                background-color: #1e293b;
                background-image: 
                    linear-gradient(180deg, rgba(15, 23, 42, 0.35) 0%, rgba(15, 23, 42, 0.75) 60%, rgba(10, 15, 25, 0.92) 100%),
                    url('https://images.unsplash.com/photo-1611273426858-450d8e3c9fce?auto=format&fit=crop&w=1600&q=80');
            }
            /* Slide 3 - Healthy green forest */
            .slide-3 {
                background-color: #064e3b;
                background-image: 
                    linear-gradient(180deg, rgba(15, 23, 42, 0.35) 0%, rgba(6, 40, 30, 0.75) 60%, rgba(3, 20, 15, 0.92) 100%),
                    url('https://images.unsplash.com/photo-1448375240586-882707db888b?auto=format&fit=crop&w=1600&q=80');
            }
            .slide-content {
                padding: 40px 48px;
                max-width: 800px;
                z-index: 2;
                animation: fadeInUp 0.8s ease forwards;
            }
            .label-badge {
                display: inline-block;
                padding: 6px 14px;
                font-size: 13px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 1.5px;
                border-radius: 9999px;
                background: rgba(0, 0, 0, 0.45);
                backdrop-filter: blur(8px);
                border: 1px solid rgba(255, 255, 255, 0.2);
                margin-bottom: 14px;
            }
            .label-fire { color: #f97316; border-color: rgba(249, 115, 22, 0.4); }
            .label-smoke { color: #facc15; border-color: rgba(250, 204, 21, 0.4); }
            .label-forest { color: #4ade80; border-color: rgba(74, 222, 128, 0.4); }

            .headline {
                font-size: 34px;
                font-weight: 800;
                color: #ffffff;
                line-height: 1.25;
                margin-bottom: 12px;
                text-shadow: 0 2px 10px rgba(0,0,0,0.7);
            }
            .subtext {
                font-size: 17px;
                font-weight: 400;
                color: #e2e8f0;
                line-height: 1.55;
                text-shadow: 0 1px 6px rgba(0,0,0,0.6);
            }
            /* Prev / Next navigation buttons */
            .nav-btn {
                position: absolute;
                top: 50%;
                transform: translateY(-50%);
                background: rgba(15, 23, 42, 0.55);
                backdrop-filter: blur(6px);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.15);
                width: 44px;
                height: 44px;
                border-radius: 50%;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 20px;
                transition: all 0.25s ease;
                z-index: 10;
                user-select: none;
            }
            .nav-btn:hover {
                background: rgba(34, 197, 94, 0.85);
                border-color: #22c55e;
                transform: translateY(-50%) scale(1.08);
            }
            .prev-btn { left: 20px; }
            .next-btn { right: 20px; }

            /* Dot indicators */
            .dots-container {
                position: absolute;
                bottom: 20px;
                right: 48px;
                display: flex;
                gap: 8px;
                z-index: 10;
            }
            .dot {
                width: 10px;
                height: 10px;
                border-radius: 50%;
                background: rgba(255, 255, 255, 0.35);
                cursor: pointer;
                transition: all 0.3s ease;
            }
            .dot.active {
                width: 32px;
                border-radius: 8px;
                background: #4ade80;
                box-shadow: 0 0 10px rgba(74, 222, 128, 0.6);
            }

            @media (max-width: 768px) {
                .carousel-container { height: 380px; }
                .slide-content { padding: 24px 20px; }
                .headline { font-size: 24px; }
                .subtext { font-size: 14px; }
                .dots-container { right: 20px; bottom: 15px; }
                .nav-btn { display: none; }
            }
        </style>
    </head>
    <body>
        <div class="carousel-container" id="carousel">
            <!-- Slide 1 -->
            <div class="slide slide-1 active" data-index="0">
                <div class="slide-content">
                    <span class="label-badge label-fire">Harder summers, heat and more fires</span>
                    <h2 class="headline">What will happen if we take no action?</h2>
                    <p class="subtext">Projects cleared without proper review can harm the Earth for generations.</p>
                </div>
            </div>

            <!-- Slide 2 -->
            <div class="slide slide-2" data-index="1">
                <div class="slide-content">
                    <span class="label-badge label-smoke">Unchecked development</span>
                    <h2 class="headline">Missed studies. Hidden risks.</h2>
                    <p class="subtext">One overlooked gap in an application can become an environmental disaster.</p>
                </div>
            </div>

            <!-- Slide 3 -->
            <div class="slide slide-3" data-index="2">
                <div class="slide-content">
                    <span class="label-badge label-forest">A better way</span>
                    <h2 class="headline">VYRO reviews. You protect.</h2>
                    <p class="subtext">AI finds the gaps so reviewers can focus on what matters.</p>
                </div>
            </div>

            <!-- Arrows -->
            <button class="nav-btn prev-btn" id="prevBtn">&#10094;</button>
            <button class="nav-btn next-btn" id="nextBtn">&#10095;</button>

            <!-- Dots -->
            <div class="dots-container" id="dotsContainer">
                <div class="dot active" data-index="0"></div>
                <div class="dot" data-index="1"></div>
                <div class="dot" data-index="2"></div>
            </div>
        </div>

        <script>
            let currentIndex = 0;
            const slides = document.querySelectorAll('.slide');
            const dots = document.querySelectorAll('.dot');
            const totalSlides = slides.length;
            let autoInterval;

            function showSlide(index) {
                slides.forEach(slide => slide.classList.remove('active'));
                dots.forEach(dot => dot.classList.remove('active'));

                currentIndex = (index + totalSlides) % totalSlides;
                slides[currentIndex].classList.add('active');
                dots[currentIndex].classList.add('active');
            }

            function nextSlide() {
                showSlide(currentIndex + 1);
            }

            function prevSlide() {
                showSlide(currentIndex - 1);
            }

            function startTimer() {
                clearInterval(autoInterval);
                autoInterval = setInterval(nextSlide, 4000);
            }

            // Events
            document.getElementById('nextBtn').addEventListener('click', () => {
                nextSlide();
                startTimer();
            });

            document.getElementById('prevBtn').addEventListener('click', () => {
                prevSlide();
                startTimer();
            });

            dots.forEach(dot => {
                dot.addEventListener('click', (e) => {
                    const idx = parseInt(e.target.getAttribute('data-index'), 10);
                    showSlide(idx);
                    startTimer();
                });
            });

            // Pause on hover
            const container = document.getElementById('carousel');
            container.addEventListener('mouseenter', () => clearInterval(autoInterval));
            container.addEventListener('mouseleave', () => startTimer());

            // Initialize auto-rotation
            startTimer();
        </script>
    </body>
    </html>
    """

    components.html(carousel_html, height=460)

    # 3. Action Area: Get Started Button
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        if st.button("🚀 Get Started →", type="primary", use_container_width=True):
            st.session_state["page"] = "login"
            st.rerun()
            
    st.markdown(
        """
        <div style="text-align: center; margin-top: 15px; color: #64748b; font-size: 0.9rem;">
            Secured access for Environmental Clearance Reviewers & Project Proponents
        </div>
        """,
        unsafe_allow_html=True
    )
