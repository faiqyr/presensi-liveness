import React, { useRef, useState, useEffect, useCallback } from 'react';
import Webcam from 'react-webcam';
import io from 'socket.io-client';
import axios from 'axios';

const socket = io('http://localhost:5000/api/presensi/stream', {
  autoConnect: false,
  transports: ['polling'],  // Gunakan polling saja untuk stabilitas (hindari error 400 WebSocket)
});

export default function PresensiPage() {
  const webcamRef = useRef(null);
  const isProcessingRef = useRef(false);
  const [isStreaming, setIsStreaming] = useState(false);
  
  const [statusData, setStatusData] = useState({
    status: 'MENUNGGU',
    blink_counter: 0,
    bbox: null,
    name: '',
    nim: '',
    message: '',
  });
  
  const [stats, setStats] = useState({ total: 0, hadir: 0, alpha: 0 });

  const fetchStats = async () => {
    try {
      const res = await axios.get('http://localhost:5000/api/dosen/statistik-presensi?pertemuan_id=1');
      if (res.data && res.data.status === 'success') {
        setStats(res.data.data);
      }
    } catch (err) {
      // Ignore silently
    }
  };

  useEffect(() => {
    fetchStats();
    const statInterval = setInterval(fetchStats, 10000); 
    return () => clearInterval(statInterval);
  }, []);

  useEffect(() => {
    let interval;
    if (isStreaming) {
      socket.io.opts.query = { pertemuan_id: 1 };
      socket.connect();
      
      socket.on('presensi_result', (data) => {
        isProcessingRef.current = false;
        setStatusData(prev => ({ ...prev, ...data }));
        if (data.status === 'SUCCESS' && data.name) {
          fetchStats();
        }
      });

      // Interval 200ms = ~5 FPS (cukup untuk deteksi kedipan, tidak membebani server)
      interval = setInterval(() => {
        if (!isProcessingRef.current) {
           captureAndSendFrame();
        }
      }, 200);
    } else {
      socket.disconnect();
      isProcessingRef.current = false;
      setStatusData({ status: 'MENUNGGU', blink_counter: 0, bbox: null, name: '', nim: '', message: '' });
      if (interval) clearInterval(interval);
    }

    return () => {
      if (interval) clearInterval(interval);
      socket.off('presensi_result');
    };
  }, [isStreaming]);

  const captureAndSendFrame = useCallback(() => {
    if (webcamRef.current) {
      const imageSrc = webcamRef.current.getScreenshot();
      if (imageSrc) {
        isProcessingRef.current = true;
        socket.emit('stream_frame', { image: imageSrc });
      }
    }
  }, []);

  const handleReset = () => {
    setStatusData({ status: 'MENUNGGU', blink_counter: 0, bbox: null, name: '', nim: '', message: '' });
  };

  const renderBoundingBox = () => {
    const { bbox, status, name, nim, blink_counter } = statusData;
    if (!bbox || !webcamRef.current || !webcamRef.current.video) return null;

    const video = webcamRef.current.video;
    if (!video.videoWidth || !video.videoHeight) return null;
    
    const scaleX = video.clientWidth / video.videoWidth;
    const scaleY = video.clientHeight / video.videoHeight;

    const [x1, y1, x2, y2] = bbox;
    const w = x2 - x1;
    const h = y2 - y1;

    // Webcam is mirrored, flip X
    const left = (video.videoWidth - x2) * scaleX;
    const top = y1 * scaleY;
    const width = w * scaleX;
    const height = h * scaleY;

    const isSuccess = status === 'SUCCESS' || status === 'ALREADY_ATTENDED';
    const boxColor = isSuccess ? '#22c55e' : '#3b82f6';

    return (
      <div 
        className="absolute z-10"
        style={{ left: `${left}px`, top: `${top}px`, width: `${width}px`, height: `${height}px` }}
      >
        {/* Info text above the bounding box */}
        {name && (
          <div className="absolute left-0 w-max flex flex-col leading-snug" style={{ bottom: `${height + 8}px` }}>
            <span className="text-blue-600 font-extrabold text-base drop-shadow-sm" style={{ textShadow: '1px 1px 2px white' }}>{name}</span>
            <span className="text-blue-600 font-bold text-sm drop-shadow-sm" style={{ textShadow: '1px 1px 2px white' }}>{nim}</span>
            {status === 'LIVENESS_FAILED_NEED_BLINK' && (
              <>
                <span className="text-red-500 font-bold text-xs mt-0.5" style={{ textShadow: '1px 1px 2px white' }}>
                  Kedip {2 - blink_counter} kali lagi
                </span>
                <span className="text-red-500 font-bold text-xs" style={{ textShadow: '1px 1px 2px white' }}>
                  Kedipan terdeteksi: {blink_counter}/2
                </span>
                <span className="text-white font-bold text-xs mt-0.5 bg-black/50 px-1 rounded" >
                  Kedipkan mata dengan jelas
                </span>
              </>
            )}
            {isSuccess && (
              <span className="text-green-600 font-bold text-sm mt-0.5" style={{ textShadow: '1px 1px 2px white' }}>
                ✅ {status === 'ALREADY_ATTENDED' ? 'Sudah Absen' : 'Presensi Berhasil'}
              </span>
            )}
          </div>
        )}

        {/* Bounding box rectangle */}
        <div 
           className="w-full h-full border-2 rounded"
           style={{ borderColor: boxColor }}
        />
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col font-sans">
      
      {/* Top Navigation Bar */}
      <div className="w-full bg-white shadow-sm py-3 px-6 flex items-center justify-start border-b border-gray-200">
        <div className="flex items-center gap-2 text-sm font-bold text-gray-700">
          <div className="w-3 h-3 bg-green-500 rounded-full"></div>
          Server Terhubung
          {isStreaming && (
            <>
              <div className="w-2 h-2 bg-red-500 rounded-full ml-4 animate-pulse"></div>
              <span className="text-red-500 text-xs font-bold">LIVE</span>
            </>
          )}
        </div>
      </div>

      <div className="flex-1 w-full max-w-7xl mx-auto p-4 md:p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* LEFT SIDE: CAMERA */}
        <div className="lg:col-span-8 flex flex-col gap-4">
          <div className="bg-white p-6 rounded-lg shadow border border-gray-200 flex flex-col">
            <h2 className="text-lg font-bold text-gray-800 mb-4">Kamera Presensi Real-time</h2>
            
            <div className="relative w-full aspect-video bg-gray-900 rounded-lg overflow-hidden border border-gray-300">
              <Webcam
                ref={webcamRef}
                audio={false}
                screenshotFormat="image/jpeg"
                screenshotQuality={0.4}
                videoConstraints={{ width: 640, height: 480, facingMode: "user" }}
                className="w-full h-full object-cover transform scale-x-[-1]"
              />
              {renderBoundingBox()}

              {/* Real-time Detection badge */}
              <div className="absolute bottom-3 right-3">
                <div className="px-3 py-1 bg-gray-800/80 rounded-full text-xs font-bold text-white flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${isStreaming ? 'bg-red-500 animate-pulse' : 'bg-gray-500'}`}></div>
                  Real-time Detection
                </div>
              </div>
            </div>

            <div className="mt-5 flex justify-center gap-3">
              {!isStreaming ? (
                <button 
                  onClick={() => setIsStreaming(true)}
                  className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded shadow transition-colors"
                >
                  Mulai Deteksi
                </button>
              ) : (
                <button 
                  onClick={() => setIsStreaming(false)}
                  className="px-6 py-2.5 bg-red-600 hover:bg-red-700 text-white font-bold rounded shadow transition-colors"
                >
                  Hentikan Deteksi
                </button>
              )}
              <button 
                onClick={handleReset}
                className="px-6 py-2.5 bg-slate-500 hover:bg-slate-600 text-white font-bold rounded shadow transition-colors"
              >
                Reset
              </button>
            </div>
          </div>
        </div>

        {/* RIGHT SIDE: STATS */}
        <div className="lg:col-span-4 flex flex-col gap-6">
          <div className="bg-white p-6 rounded-lg shadow border border-gray-200 flex-1 flex flex-col">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-lg font-bold text-gray-800">Sudah Absen</h2>
              <span className="text-sm font-semibold text-gray-500">{stats.hadir}/{stats.total}</span>
            </div>
            
            <div className="grid grid-cols-3 gap-2">
              <div className="bg-green-50 rounded py-3 flex flex-col items-center justify-center text-center">
                <span className="text-xl font-bold text-green-600">{stats.hadir}</span>
                <span className="text-xs font-medium text-gray-600 mt-1">Hadir</span>
              </div>
              <div className="bg-red-50 rounded py-3 flex flex-col items-center justify-center text-center">
                <span className="text-xl font-bold text-red-600">{stats.alpha}</span>
                <span className="text-xs font-medium text-gray-600 mt-1">Alpha</span>
              </div>
              <div className="bg-gray-50 rounded py-3 flex flex-col items-center justify-center text-center">
                <span className="text-xl font-bold text-gray-600">{stats.total}</span>
                <span className="text-xs font-medium text-gray-600 mt-1">Total</span>
              </div>
            </div>

            <div className="flex-1 flex flex-col items-center justify-center mt-10 text-gray-400">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 mb-2 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
              <p className="text-sm font-medium">Belum ada mahasiswa yang absen</p>
            </div>
            
          </div>
        </div>

      </div>
    </div>
  );
}
