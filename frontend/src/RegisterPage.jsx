import React, { useRef, useState, useCallback } from 'react';
import Webcam from 'react-webcam';
import axios from 'axios';

const POSES = [
  { id: 'front', label: 'Wajah Depan', instruction: 'Tatap lurus ke kamera.' },
  { id: 'left', label: 'Menoleh Kiri', instruction: 'Tolehkan wajah Anda ke kiri.' },
  { id: 'right', label: 'Menoleh Kanan', instruction: 'Tolehkan wajah Anda ke kanan.' },
  { id: 'up', label: 'Menghadap Atas', instruction: 'Angkat dagu Anda ke atas.' },
  { id: 'down', label: 'Menghadap Bawah', instruction: 'Tundukkan wajah Anda ke bawah.' }
];

export default function RegisterPage() {
  const webcamRef = useRef(null);
  const [formData, setFormData] = useState({ nim: '', nama: '', kelas_id: 1 });
  const [capturedImages, setCapturedImages] = useState([]);
  const [currentPoseIndex, setCurrentPoseIndex] = useState(0);
  
  const [status, setStatus] = useState({ type: '', message: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const capture = useCallback(() => {
    if (webcamRef.current) {
      const imageSrc = webcamRef.current.getScreenshot();
      if (imageSrc) {
        setCapturedImages(prev => [...prev, imageSrc]);
        setCurrentPoseIndex(prev => prev + 1);
      }
    }
  }, [webcamRef]);

  const resetPhotos = () => {
    setCapturedImages([]);
    setCurrentPoseIndex(0);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const submitRegistration = async (e) => {
    e.preventDefault();
    if (!formData.nim || !formData.nama || capturedImages.length < 5) {
      setStatus({ type: 'error', message: 'NIM, Nama, dan 5 Foto wajah harus lengkap!' });
      return;
    }

    setIsSubmitting(true);
    setStatus({ type: 'info', message: 'Memproses pendaftaran 5 wajah ke database...' });

    try {
      const response = await axios.post('http://localhost:5000/api/admin/register-face', {
        nim: formData.nim,
        nama: formData.nama,
        kelas_id: parseInt(formData.kelas_id),
        images_base64: capturedImages // Send array of 5 images
      });

      setStatus({ type: 'success', message: response.data.message });
      // Reset form
      setFormData({ nim: '', nama: '', kelas_id: 1 });
      resetPhotos();
    } catch (error) {
      const errorMsg = error.response?.data?.message || error.message;
      setStatus({ type: 'error', message: `Gagal mendaftarkan: ${errorMsg}` });
    } finally {
      setIsSubmitting(false);
    }
  };

  const currentPose = POSES[currentPoseIndex];

  return (
    <div className="p-6 md:p-10 flex flex-col items-center">
      <header className="w-full max-w-6xl mb-8 text-center border-b border-slate-700 pb-4">
        <h2 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-blue-500">
          Registrasi Wajah (5 Pose)
        </h2>
        <p className="text-slate-400 mt-2">Daftarkan wajah dengan 5 sudut berbeda untuk akurasi presensi yang maksimal</p>
      </header>

      <div className="w-full max-w-6xl grid grid-cols-1 lg:grid-cols-12 gap-8">
        
        {/* Left Side: Form */}
        <div className="lg:col-span-4 bg-slate-800/60 p-8 rounded-2xl shadow-xl border border-slate-700 backdrop-blur-sm h-fit">
          <form onSubmit={submitRegistration} className="flex flex-col gap-5">
            <div>
              <label className="block text-sm font-semibold text-slate-300 mb-2">NIM</label>
              <input 
                type="text" name="nim" value={formData.nim} onChange={handleInputChange}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-4 py-3 text-slate-100 focus:outline-none focus:border-emerald-500"
                placeholder="Masukkan NIM..." required
              />
            </div>
            
            <div>
              <label className="block text-sm font-semibold text-slate-300 mb-2">Nama Lengkap</label>
              <input 
                type="text" name="nama" value={formData.nama} onChange={handleInputChange}
                className="w-full bg-slate-900 border border-slate-600 rounded-lg px-4 py-3 text-slate-100 focus:outline-none focus:border-emerald-500"
                placeholder="Masukkan Nama Lengkap..." required
              />
            </div>

            {/* Status Message */}
            {status.message && (
              <div className={`p-4 rounded-lg font-medium text-sm ${
                status.type === 'success' ? 'bg-emerald-900/30 text-emerald-400 border border-emerald-500/30' :
                status.type === 'error' ? 'bg-rose-900/30 text-rose-400 border border-rose-500/30' :
                'bg-blue-900/30 text-blue-400 border border-blue-500/30'
              }`}>
                {status.message}
              </div>
            )}

            <button 
              type="submit" 
              disabled={isSubmitting || capturedImages.length < 5}
              className={`mt-4 px-6 py-4 font-bold rounded-xl shadow-lg transition-all ${
                isSubmitting || capturedImages.length < 5
                  ? 'bg-slate-700 text-slate-500 cursor-not-allowed'
                  : 'bg-gradient-to-r from-emerald-600 to-blue-600 hover:from-emerald-500 hover:to-blue-500 text-white transform hover:-translate-y-1'
              }`}
            >
              {isSubmitting ? 'Mendaftarkan...' : 'Simpan Data Wajah'}
            </button>
          </form>
        </div>

        {/* Right Side: Camera & Gallery */}
        <div className="lg:col-span-8 flex flex-col gap-4">
          <div className="bg-slate-800/60 p-6 rounded-2xl shadow-xl border border-slate-700 relative overflow-hidden backdrop-blur-sm">
            
            {/* Progress Header */}
            <div className="flex justify-between items-center mb-6">
              <div>
                <h3 className="text-xl font-bold text-slate-200">
                  {currentPoseIndex < 5 ? `Langkah ${currentPoseIndex + 1} dari 5: ${currentPose.label}` : 'Pengambilan Selesai! 🎉'}
                </h3>
                <p className="text-emerald-400 text-sm mt-1 font-medium">
                  {currentPoseIndex < 5 ? currentPose.instruction : 'Silakan klik Simpan Data Wajah di sebelah kiri.'}
                </p>
              </div>
              <div className="flex gap-1">
                {[0, 1, 2, 3, 4].map(idx => (
                  <div key={idx} className={`h-2 w-8 rounded-full transition-all duration-300 ${
                    idx < currentPoseIndex ? 'bg-emerald-500' : idx === currentPoseIndex ? 'bg-blue-500 animate-pulse' : 'bg-slate-600'
                  }`} />
                ))}
              </div>
            </div>

            {/* Camera Viewport */}
            <div className="relative w-full aspect-video bg-black rounded-xl overflow-hidden border-2 border-slate-700 shadow-inner">
              {currentPoseIndex < 5 ? (
                <>
                  <Webcam
                    ref={webcamRef}
                    audio={false}
                    screenshotFormat="image/jpeg"
                    videoConstraints={{ facingMode: "user" }}
                    className="w-full h-full object-cover transform scale-x-[-1]"
                  />
                  {/* Overlay Guide */}
                  <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                     <div className="w-48 h-64 border-4 border-dashed border-white/40 rounded-full"></div>
                     <span className="mt-4 bg-black/60 px-4 py-2 rounded-lg text-white font-bold backdrop-blur-sm shadow-lg">
                       {currentPose.label}
                     </span>
                  </div>
                </>
              ) : (
                <div className="w-full h-full flex flex-col items-center justify-center bg-emerald-900/20 text-emerald-400">
                  <div className="text-5xl mb-4">✅</div>
                  <h3 className="text-2xl font-bold">5 Pose Berhasil Direkam</h3>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="mt-6 flex justify-center gap-4">
              {currentPoseIndex < 5 ? (
                <button 
                  onClick={capture}
                  className="px-10 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold rounded-lg shadow-lg shadow-blue-500/30 transition-transform transform hover:scale-105"
                >
                  📸 Ambil Foto {currentPose.label}
                </button>
              ) : (
                <button 
                  onClick={resetPhotos}
                  className="px-10 py-3 bg-rose-600 hover:bg-rose-500 text-white font-bold rounded-lg shadow-lg shadow-rose-500/30 transition-transform transform hover:scale-105"
                >
                  🔄 Ulangi Pengambilan
                </button>
              )}
            </div>

            {/* Gallery Miniatures */}
            <div className="mt-8">
              <h4 className="text-sm font-semibold text-slate-400 mb-3 uppercase tracking-wider">Hasil Jepretan:</h4>
              <div className="flex gap-4 overflow-x-auto pb-4 custom-scrollbar">
                {POSES.map((pose, idx) => (
                  <div key={idx} className={`relative flex-shrink-0 w-24 h-24 rounded-lg overflow-hidden border-2 ${idx < currentPoseIndex ? 'border-emerald-500' : 'border-slate-700 bg-slate-800 border-dashed'}`}>
                    {idx < currentPoseIndex ? (
                      <img src={capturedImages[idx]} alt={pose.label} className="w-full h-full object-cover transform scale-x-[-1]" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-slate-600 text-xs text-center p-2">
                        {pose.label}
                      </div>
                    )}
                    {idx < currentPoseIndex && (
                      <div className="absolute bottom-0 w-full bg-black/60 text-white text-[10px] text-center py-1">
                        {pose.label}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

          </div>
        </div>

      </div>
    </div>
  );
}
