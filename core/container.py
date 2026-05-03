# core/container.py
"""
AppContainer — Dependency Injection Container đơn giản cho QLCTDT.
Quản lý lifetime của các service, tránh global state rải rác.

Sử dụng:
    container = AppContainer(db_path='qlctdt.db')
    
    # Trong main window:
    self.db             = container.db
    self.template_svc   = container.template_svc
    self.version_svc    = container.version_svc
    self.stats_svc      = container.stats_svc
    self.worker_pool    = container.worker_pool
    self.cache          = container.cache
    self.events         = container.events
"""


class AppContainer:
    """
    Lightweight DI container.
    Lazy initialize services — chỉ khởi tạo khi được access lần đầu.
    """

    def __init__(self, db_path: str = None):
        self._db_path = db_path
        self._db = None
        self._cache = None
        self._template_svc = None
        self._version_svc = None
        self._stats_svc = None
        self._worker_pool = None
        self._events = None
        self._validation_svc = None
        self._deccuong_svc = None
        
        # Repositories
        self._hp_repo = None
        self._khoa_repo = None
        self._gv_repo = None
        self._clo_repo = None
        self._tailieu_repo = None
        self._noidung_repo = None
        self._rubric_repo = None
        self._baidanhgia_repo = None


    # ── Data Layer ────────────────────────────────────────────────────────────

    @property
    def db(self):
        """Singleton Database instance."""
        if self._db is None:
            from db import Database
            self._db = Database(self._db_path)
        return self._db

    @property
    def cache(self):
        """Singleton TTLCache."""
        if self._cache is None:
            from services.cache_service import TTLCache
            self._cache = TTLCache(default_ttl=120)
        return self._cache

    # ── Async & Events ────────────────────────────────────────────────────────

    @property
    def worker_pool(self):
        """Singleton WorkerPool."""
        if self._worker_pool is None:
            from utils.async_worker import WorkerPool
            self._worker_pool = WorkerPool(max_workers=2)
        return self._worker_pool

    @property
    def events(self):
        """EventBus class (stateless, no need to instantiate)."""
        from utils.event_bus import EventBus
        return EventBus

    # ── Services ──────────────────────────────────────────────────────────────

    @property
    def template_svc(self):
        """Lazy TemplateService."""
        if self._template_svc is None:
            from services.template_service import TemplateService
            self._template_svc = TemplateService(self.db)
        return self._template_svc

    @property
    def version_svc(self):
        """Lazy VersionService."""
        if self._version_svc is None:
            from services.version_service import VersionService
            self._version_svc = VersionService(self.db)
        return self._version_svc

    @property
    def stats_svc(self):
        """Lazy StatsService."""
        if self._stats_svc is None:
            from services.stats_service import StatsService
            self._stats_svc = StatsService(self.db)
        return self._stats_svc

    @property
    def validation_svc(self):
        """Lazy ValidationService."""
        if self._validation_svc is None:
            from services.validation_service import ValidationService
            self._validation_svc = ValidationService
        return self._validation_svc

    @property
    def deccuong_svc(self):
        """Lazy DeCuongService."""
        if self._deccuong_svc is None:
            from services.deccuong_service import DeCuongService
            self._deccuong_svc = DeCuongService(self.db)
        return self._deccuong_svc

    # ── Repositories ──────────────────────────────────────────────────────────

    @property
    def hp_repo(self):
        if self._hp_repo is None:
            from repositories.hoc_phan_repository import HocPhanRepository
            self._hp_repo = HocPhanRepository(self.db)
        return self._hp_repo

    @property
    def khoa_repo(self):
        if self._khoa_repo is None:
            from repositories.khoa_repository import KhoaRepository
            self._khoa_repo = KhoaRepository(self.db)
        return self._khoa_repo

    @property
    def gv_repo(self):
        if self._gv_repo is None:
            from repositories.giang_vien_repository import GiangVienRepository
            self._gv_repo = GiangVienRepository(self.db)
        return self._gv_repo

    @property
    def clo_repo(self):
        if self._clo_repo is None:
            from repositories.clo_repository import CLORepository
            self._clo_repo = CLORepository(self.db)
        return self._clo_repo

    @property
    def tailieu_repo(self):
        if self._tailieu_repo is None:
            from repositories.tailieu_repository import TaiLieuRepository
            self._tailieu_repo = TaiLieuRepository(self.db)
        return self._tailieu_repo

    @property
    def noidung_repo(self):
        if self._noidung_repo is None:
            from repositories.noidung_repository import NoiDungRepository
            self._noidung_repo = NoiDungRepository(self.db)
        return self._noidung_repo

    @property
    def rubric_repo(self):
        if self._rubric_repo is None:
            from repositories.rubric_repository import RubricRepository
            self._rubric_repo = RubricRepository(self.db)
        return self._rubric_repo


    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def shutdown(self):
        """Dọn dẹp khi thoát app."""
        if self._worker_pool:
            self._worker_pool.shutdown()
        if self._cache:
            self._cache.clear()
        print("[AppContainer] Shutdown complete.")

    def cache_stats(self) -> dict:
        """Thống kê cache để debug."""
        return self.cache.stats()

    def warm_up(self):
        """
        Khởi tạo sẵn các service hay dùng để tránh latency lần đầu.
        Gọi sau khi app window hiển thị (không block startup).
        """
        _ = self.db
        _ = self.cache
        _ = self.worker_pool
        # Pre-warm essential repos
        _ = self.hp_repo
        _ = self.khoa_repo
        print("[AppContainer] Warm-up done.")



# Singleton toàn app
_app_container: 'AppContainer' = None


def get_container() -> AppContainer:
    """Lấy singleton AppContainer."""
    global _app_container
    if _app_container is None:
        _app_container = AppContainer()
    return _app_container


def init_container(db_path: str) -> AppContainer:
    """Khởi tạo AppContainer với db_path cụ thể (gọi khi start app)."""
    global _app_container
    _app_container = AppContainer(db_path=db_path)
    return _app_container
