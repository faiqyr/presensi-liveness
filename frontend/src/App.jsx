import React, { useState } from 'react';
import PresensiPage from './PresensiPage';
import RegisterPage from './RegisterPage';
import { Camera, UserPlus } from 'lucide-react';

function App() {
  const [currentPage, setCurrentPage] = useState('presensi');

  return (
    <div className="min-h-screen flex flex-col bg-slate-900 text-slate-50">
      {/* Navigation Bar */}
      <nav className="w-full bg-slate-800/80 border-b border-slate-700 p-4 sticky top-0 z-50 backdrop-blur-md shadow-lg">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-emerald-500 rounded-xl flex items-center justify-center shadow-lg">
              <Camera className="text-white" size={20} />
            </div>
            <h1 className="text-xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-emerald-400 hidden sm:block">
              Face System
            </h1>
          </div>
          
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentPage('presensi')}
              className={`px-4 py-2 rounded-lg font-semibold transition-all flex items-center gap-2 ${
                currentPage === 'presensi' 
                  ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/30' 
                  : 'bg-slate-700/50 text-slate-300 hover:bg-slate-700'
              }`}
            >
              <Camera size={18} />
              Absen
            </button>
            <button
              onClick={() => setCurrentPage('register')}
              className={`px-4 py-2 rounded-lg font-semibold transition-all flex items-center gap-2 ${
                currentPage === 'register' 
                  ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-500/30' 
                  : 'bg-slate-700/50 text-slate-300 hover:bg-slate-700'
              }`}
            >
              <UserPlus size={18} />
              Registrasi Wajah
            </button>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="flex-1 w-full">
        {currentPage === 'presensi' ? <PresensiPage /> : <RegisterPage />}
      </main>
    </div>
  );
}

export default App;
