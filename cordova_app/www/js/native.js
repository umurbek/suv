document.addEventListener('deviceready', function () {
  const logEl = document.getElementById('log');
  function writeLog(msg){
    console.log(msg);
    if(logEl) logEl.innerText = msg;
  }

  const perms = (window.cordova && window.cordova.plugins && window.cordova.plugins.permissions) ? window.cordova.plugins.permissions : null;

  function ensurePermission(permission, cb){
    if(!perms){ cb && cb(false); return; }
    perms.hasPermission(permission, function(status){
      if(status.hasPermission){ cb && cb(true); }
      else{ perms.requestPermission(permission, function(){ cb && cb(true); }, function(){ cb && cb(false); }); }
    }, function(){ cb && cb(false); });
  }

  async function takePhoto(){
    if(!navigator.camera){ writeLog('Camera plugin mavjud emas'); return; }
    ensurePermission(perms ? perms.CAMERA : null, function(ok){
      if(!ok){ writeLog('Kamera ruxsati yo\'q'); return; }
      navigator.camera.getPicture(function(imageData){
        // imageData is base64 string
        const img = document.createElement('img');
        img.src = 'data:image/jpeg;base64,' + imageData;
        img.style.maxWidth = '100%';
        document.body.appendChild(img);
        writeLog('Rasm olindi');
      }, function(err){ writeLog('Camera xato: '+err); }, {
        quality: 60,
        destinationType: Camera.DestinationType.DATA_URL,
        encodingType: Camera.EncodingType.JPEG,
        correctOrientation: true
      });
    });
  }

  function getLocation(){
    if(!navigator.geolocation){ writeLog('Geolocation plugin mavjud emas'); return; }
    ensurePermission(perms ? perms.ACCESS_FINE_LOCATION : null, function(ok){
      if(!ok){ writeLog('Location ruxsati yo\'q'); return; }
      navigator.geolocation.getCurrentPosition(function(pos){
        writeLog('Lat: '+pos.coords.latitude+' Lon: '+pos.coords.longitude+' Acc: '+pos.coords.accuracy);
      }, function(err){ writeLog('Geo xato: '+err.message); }, { enableHighAccuracy: true, timeout: 10000 });
    });
  }

  function registerPush(){
    const fb = window.FirebasePlugin || window.firebase || null;
    if(!fb){ writeLog('Firebase plugin o\'rnatilmagan'); return; }

    // Android 13+ notification permission
    if(window.AndroidPermissions && window.AndroidPermissions.requestPermission){
      try{
        const PostNotif = 'android.permission.POST_NOTIFICATIONS';
        ensurePermission(PostNotif, function(ok){ if(!ok) writeLog('Notification permission denied'); });
      }catch(e){ }
    }

    fb.getToken(function(token){
      writeLog('FCM token: '+token);
      // Send token to backend so you can target this device
      try{
        fetch(window.API_BASE + 'client_panel/api/register_push_token/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: token })
        }).then(r=>r.text()).then(t=>console.log('server resp', t)).catch(e=>console.warn(e));
      }catch(e){ console.warn(e); }
    }, function(err){ writeLog('getToken xato: '+err); });

    fb.onMessageReceived(function(payload){
      console.log('Push message', payload);
      if(payload && payload.notification){
        writeLog('Push: '+(payload.notification.title || '')+' - '+(payload.notification.body || ''));
      }else{
        writeLog('Push kelishi: '+JSON.stringify(payload));
      }
    }, function(err){ console.warn('onMessageReceived err', err); });
  }

  // Hook buttons
  const btnCam = document.getElementById('btnCamera');
  const btnLoc = document.getElementById('btnLocation');
  const btnPush = document.getElementById('btnRegisterPush');
  if(btnCam) btnCam.addEventListener('click', takePhoto);
  if(btnLoc) btnLoc.addEventListener('click', getLocation);
  if(btnPush) btnPush.addEventListener('click', registerPush);

  writeLog('Device ready — native functions available');
});
