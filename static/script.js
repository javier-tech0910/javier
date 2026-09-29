document.addEventListener('DOMContentLoaded', () => {
    // Likes
    document.querySelectorAll('.boton-like').forEach(btn => btn.addEventListener('click', async () => {
        const post = btn.closest('.publicacion');
        if (!post) return;
        try {
            const r = await fetch(`/like/${post.dataset.publicacionId}`, {method:'POST'});
            const d = await r.json();
            if (!r.ok) return;
            btn.classList.toggle('liked', d.liked);
            btn.innerHTML = `${d.liked ? '♥' : '♡'} <span class="contador-likes">${d.likes}</span>`;
        } catch (e) { console.error(e); }
    }));

    // Guardados
    document.querySelectorAll('.boton-guardar').forEach(btn => btn.addEventListener('click', async () => {
        const post = btn.closest('.publicacion');
        if (!post) return;
        try {
            const r = await fetch(`/guardar/${post.dataset.publicacionId}`, {method:'POST'});
            const d = await r.json();
            if (r.ok) {
                btn.classList.toggle('saved', d.saved);
                btn.textContent = d.saved ? '▣' : '□';
            }
        } catch (e) { console.error(e); }
    }));

    // Comentarios
    document.querySelectorAll('.boton-comentarios').forEach(btn => btn.addEventListener('click', () => {
        const p = btn.closest('.publicacion');
        const box = p?.querySelector('.comentarios');
        if (box) box.style.display = box.style.display === 'none' || !box.style.display ? 'block' : 'none';
    }));

    document.querySelectorAll('.boton-publicar-comentario').forEach(btn => btn.addEventListener('click', async () => {
        const p = btn.closest('.publicacion');
        const input = p.querySelector('.input-comentario');
        const text = input.value.trim();
        if (!text) return;
        try {
            const r = await fetch(`/comentario/${p.dataset.publicacionId}`, {
                method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({comentario:text})
            });
            const d = await r.json();
            if (!r.ok) return;
            const item = document.createElement('div');
            item.className = 'comentario';
            item.innerHTML = `<span class="avatar avatar-sm">${d.foto_perfil ? `<img src="/uploads/${encodeURIComponent(d.foto_perfil)}">` : escapeHtml((d.nombre || 'V')[0].toUpperCase())}</span><div><strong>${escapeHtml(d.username || d.nombre)}</strong> ${escapeHtml(d.comentario)}<small>${d.fecha}</small></div>`;
            p.querySelector('.lista-comentarios').appendChild(item);
            input.value = '';
            p.querySelector('.comentarios').style.display = 'block';
        } catch (e) { console.error(e); }
    }));

    // Seguir
    document.querySelectorAll('.boton-seguir').forEach(btn => btn.addEventListener('click', async () => {
        try {
            const r = await fetch(`/seguir/${btn.dataset.usuarioId}`, {method:'POST'});
            const d = await r.json();
            if (!r.ok) return;
            btn.textContent = d.siguiendo ? 'Dejar de seguir' : 'Seguir';
            const c = document.querySelector('.contador-seguidores');
            if (c) c.textContent = d.seguidores;
        } catch (e) { console.error(e); }
    }));

    // Menús de los tres puntos
    document.querySelectorAll('.post-menu-button').forEach(btn => btn.addEventListener('click', e => {
        e.stopPropagation();
        const menu = btn.closest('.post-menu-wrap')?.querySelector('.post-menu');
        document.querySelectorAll('.post-menu.open').forEach(m => { if (m !== menu) m.classList.remove('open'); });
        menu?.classList.toggle('open');
    }));
    document.addEventListener('click', () => document.querySelectorAll('.post-menu.open').forEach(m => m.classList.remove('open')));

    // Eliminar publicación propia
    document.querySelectorAll('.eliminar-publicacion').forEach(btn => btn.addEventListener('click', async e => {
        e.stopPropagation();
        const id = btn.dataset.publicacionId;
        if (!confirm('¿Seguro que quieres eliminar esta publicación? Esta acción no se puede deshacer.')) return;
        try {
            const r = await fetch(`/api/publicacion/${id}/eliminar`, {method:'POST'});
            const d = await r.json();
            if (r.ok && d.ok) {
                btn.closest('.publicacion')?.remove();
            }
        } catch (err) { console.error(err); }
    }));

    // Copiar enlace
    const copiar = async url => {
        try {
            await navigator.clipboard.writeText(url);
            showToast('Enlace copiado');
        } catch {
            window.prompt('Copia este enlace:', url);
        }
    };
    document.querySelectorAll('.copiar-enlace, .copiar-enlace-action').forEach(btn => btn.addEventListener('click', e => {
        e.preventDefault(); e.stopPropagation(); copiar(btn.dataset.url);
    }));

    // Selector de archivos bonito
    document.querySelectorAll('.file-input').forEach(input => input.addEventListener('change', () => {
        const name = input.closest('.upload-box')?.querySelector('.file-name');
        if (name) name.textContent = input.files?.length ? input.files[0].name : name.dataset.default;
        document.querySelectorAll('.file-input').forEach(other => {
            if (other !== input) {
                const otherName = other.closest('.upload-box')?.querySelector('.file-name');
                if (otherName) otherName.textContent = otherName.dataset.default;
            }
        });
    }));

    // Historias
    const storyButtons = [...document.querySelectorAll('.story-open')];
    const viewer = document.getElementById('storyViewer');
    if (viewer && storyButtons.length) {
        let storyIndex = 0;
        const userEl = document.getElementById('storyViewerUser');
        const textEl = document.getElementById('storyViewerText');
        const mediaEl = document.getElementById('storyViewerMedia');
        const renderStory = index => {
            storyIndex = (index + storyButtons.length) % storyButtons.length;
            const b = storyButtons[storyIndex];
            userEl.textContent = b.dataset.storyUser || 'VIBRA';
            textEl.textContent = b.dataset.storyText || '';
            mediaEl.innerHTML = '';
            if (b.dataset.storyType === 'video') {
                const video = document.createElement('video');
                video.src = b.dataset.storySrc; video.controls = true; video.autoplay = true; video.playsInline = true;
                mediaEl.appendChild(video);
            } else {
                const img = document.createElement('img'); img.src = b.dataset.storySrc; img.alt = 'Historia'; mediaEl.appendChild(img);
            }
            viewer.classList.add('open'); viewer.setAttribute('aria-hidden','false'); document.body.classList.add('modal-open');
        };
        storyButtons.forEach((b,i) => b.addEventListener('click', () => renderStory(i)));
        document.getElementById('storyViewerClose')?.addEventListener('click', closeStory);
        document.getElementById('storyPrev')?.addEventListener('click', () => renderStory(storyIndex - 1));
        document.getElementById('storyNext')?.addEventListener('click', () => renderStory(storyIndex + 1));
        viewer.addEventListener('click', e => { if (e.target === viewer) closeStory(); });
        document.addEventListener('keydown', e => { if (!viewer.classList.contains('open')) return; if(e.key==='Escape') closeStory(); if(e.key==='ArrowLeft') renderStory(storyIndex-1); if(e.key==='ArrowRight') renderStory(storyIndex+1); });
        function closeStory(){ viewer.classList.remove('open'); viewer.setAttribute('aria-hidden','true'); document.body.classList.remove('modal-open'); mediaEl.innerHTML=''; }
    }

    function showToast(message) {
        let toast = document.getElementById('vibraToast');
        if (!toast) { toast = document.createElement('div'); toast.id='vibraToast'; toast.className='vibra-toast'; document.body.appendChild(toast); }
        toast.textContent = message; toast.classList.add('show'); setTimeout(()=>toast.classList.remove('show'),1800);
    }
});
function escapeHtml(s){const d=document.createElement('div');d.textContent=s??'';return d.innerHTML;}
if('serviceWorker' in navigator) window.addEventListener('load',()=>navigator.serviceWorker.register('/service-worker.js').catch(()=>{}));

/* ===== CREAR PUBLICACIÓN · PREVISUALIZACIÓN 2.1 ===== */
document.addEventListener('DOMContentLoaded', () => {
    const createForm = document.getElementById('createForm');
    if (!createForm) return;

    const imageInput = document.getElementById('imageInput');
    const videoInput = document.getElementById('videoInput');
    const imageCard = document.querySelector('[data-upload-card="image"]');
    const videoCard = document.querySelector('[data-upload-card="video"]');
    const imageEmpty = document.getElementById('imageEmpty');
    const videoEmpty = document.getElementById('videoEmpty');
    const imagePreview = document.getElementById('imagePreview');
    const videoPreview = document.getElementById('videoPreview');
    const imageName = document.getElementById('imageName');
    const videoName = document.getElementById('videoName');
    const status = document.getElementById('mediaStatus');
    const description = createForm.querySelector('textarea[name="descripcion"]');
    const descriptionCount = document.getElementById('descriptionCount');
    let imageUrl = null;
    let videoUrl = null;

    const resetImage = () => {
        imageInput.value = '';
        imagePreview.hidden = true;
        imagePreview.querySelector('img').removeAttribute('src');
        imageEmpty.hidden = false;
        imageCard.classList.remove('has-media');
        imageName.textContent = 'Ninguna imagen seleccionada';
        if (imageUrl) { URL.revokeObjectURL(imageUrl); imageUrl = null; }
    };

    const resetVideo = () => {
        videoInput.value = '';
        videoPreview.hidden = true;
        const video = videoPreview.querySelector('video');
        video.pause();
        video.removeAttribute('src');
        video.load();
        videoEmpty.hidden = false;
        videoCard.classList.remove('has-media');
        videoName.textContent = 'Ningún video seleccionado';
        if (videoUrl) { URL.revokeObjectURL(videoUrl); videoUrl = null; }
    };

    const updateStatus = () => {
        const hasImage = !!imageInput.files?.length;
        const hasVideo = !!videoInput.files?.length;
        if (!hasImage && !hasVideo) {
            status.textContent = 'Sin archivo';
            status.classList.remove('ready');
        } else {
            status.textContent = hasImage ? 'Imagen lista' : 'Video listo';
            status.classList.add('ready');
        }
    };

    const previewImage = file => {
        if (!file) return resetImage();
        resetVideo();
        if (imageUrl) URL.revokeObjectURL(imageUrl);
        imageUrl = URL.createObjectURL(file);
        imagePreview.querySelector('img').src = imageUrl;
        imagePreview.hidden = false;
        imageEmpty.hidden = true;
        imageCard.classList.add('has-media');
        imageName.textContent = file.name;
        updateStatus();
    };

    const previewVideo = file => {
        if (!file) return resetVideo();
        resetImage();
        if (videoUrl) URL.revokeObjectURL(videoUrl);
        videoUrl = URL.createObjectURL(file);
        const video = videoPreview.querySelector('video');
        video.src = videoUrl;
        videoPreview.hidden = false;
        videoEmpty.hidden = true;
        videoCard.classList.add('has-media');
        videoName.textContent = file.name;
        updateStatus();
    };

    imageInput?.addEventListener('change', () => previewImage(imageInput.files?.[0]));
    videoInput?.addEventListener('change', () => previewVideo(videoInput.files?.[0]));

    [imageCard, videoCard].forEach(card => {
        if (!card) return;
        card.addEventListener('dragover', e => { e.preventDefault(); card.classList.add('dragging'); });
        card.addEventListener('dragleave', () => card.classList.remove('dragging'));
        card.addEventListener('drop', e => {
            e.preventDefault();
            card.classList.remove('dragging');
            const file = e.dataTransfer.files?.[0];
            if (!file) return;
            if (card === imageCard && file.type.startsWith('image/')) {
                const transfer = new DataTransfer(); transfer.items.add(file); imageInput.files = transfer.files; previewImage(file);
            } else if (card === videoCard && file.type.startsWith('video/')) {
                const transfer = new DataTransfer(); transfer.items.add(file); videoInput.files = transfer.files; previewVideo(file);
            } else {
                showCreateToast(card === imageCard ? 'Suelta una imagen válida.' : 'Suelta un video válido.');
            }
        });
    });

    description?.addEventListener('input', () => { descriptionCount.textContent = description.value.length; });
    description?.dispatchEvent(new Event('input'));

createForm.addEventListener('submit', async e => {
    const hasImage = !!imageInput.files?.length;
    const hasVideo = !!videoInput.files?.length;

    if (!hasImage && !hasVideo) {
        e.preventDefault();
        showCreateToast('Selecciona una imagen o un video antes de publicar.');
        return;
    }

    // Si es una imagen, dejamos el formulario funcionando como antes.
    if (hasImage && !hasVideo) {
        const button = document.getElementById('publishButton');
        if (button) {
            button.disabled = true;
            button.style.opacity = '.65';
            button.querySelector('span').textContent = 'Publicando…';
        }
        return;
    }

    // Si es video, NO lo enviamos a Flask.
    if (hasVideo) {
        e.preventDefault();

        const button = document.getElementById('publishButton');

        if (button) {
            button.disabled = true;
            button.style.opacity = '.65';
            button.querySelector('span').textContent = 'Subiendo video…';
        }

        try {
            const video = videoInput.files[0];

            // 1. Pedimos a Flask una URL temporal para el Bucket.
            const response = await fetch('/api/video-upload-url', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    filename: video.name,
                    content_type: video.type || 'video/mp4'
                })
            });

            const uploadData = await response.json();

            if (!response.ok) {
                throw new Error(uploadData.error || 'No se pudo preparar la subida.');
            }

            // 2. Subimos el video directamente al Bucket.
            if (button) {
                button.querySelector('span').textContent = 'Subiendo video…';
            }

const uploadResponse = await new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    xhr.open('PUT', uploadData.url, true);
    xhr.setRequestHeader('Content-Type', video.type || 'video/mp4');

    xhr.upload.onprogress = (event) => {
        if (event.lengthComputable && button) {
            const porcentaje = Math.round((event.loaded / event.total) * 100);
            button.querySelector('span').textContent = `Subiendo video… ${porcentaje}%`;
        }
    };

    xhr.onload = () => {
        resolve({
            ok: xhr.status >= 200 && xhr.status < 300
        });
    };

    xhr.onerror = () => {
        reject(new Error('No se pudo subir el video al Bucket.'));
    };

    xhr.send(video);
});

if (!uploadResponse.ok) {
    throw new Error('El Bucket rechazó la subida del video.');
}
            // 3. Creamos el FormData SIN el archivo de video.
            const formData = new FormData(createForm);

            formData.delete('video');
            formData.append('video_key', uploadData.key);

            if (button) {
                button.querySelector('span').textContent = 'Publicando…';
            }

            // 4. Flask recibe solamente la referencia al video.
            const publishResponse = await fetch(createForm.action, {
                method: 'POST',
                body: formData
            });

            if (!publishResponse.ok) {
                throw new Error('No se pudo crear la publicación.');
            }

            // 5. Volvemos a la página principal.
            window.location.href = publishResponse.url;

        } catch (error) {
            console.error('Error subiendo video:', error);

            if (button) {
                button.disabled = false;
                button.style.opacity = '';
                button.querySelector('span').textContent = 'Publicar';
            }

            showCreateToast(error.message || 'Error al subir el video.');
        }
    }
});
});
