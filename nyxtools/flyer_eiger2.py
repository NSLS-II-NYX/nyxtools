import logging
import time as ttime

from mxtools.flyer import MXFlyer
from ophyd.status import SubscriptionStatus

logger = logging.getLogger(__name__)
DEFAULT_DATUM_DICT = {"data": None, "omega": None}


class NYXEiger2Flyer(MXFlyer):
    def __init__(self, vector, zebra, detector=None) -> None:
        super().__init__(vector, zebra, detector)
        self.name = "NYXEiger2Flyer"

    def kickoff(self):
        self.detector.stage()
        st = self.vector.move()
        return st

    def update_parameters(self, **kwargs):
        super().update_parameters(**kwargs)

        def armed_callback(value, old_value, **kwargs):
            if old_value == 0 and value == 1:
                return True
            return False

        zebra_status = SubscriptionStatus(self.zebra.pc.arm.output, armed_callback, run=False)
        self.zebra.pc.arm_signal.put(1)
        zebra_status.wait()

    def complete(self):
        def callback_motion(value, old_value, **kwargs):
            print(f"old: {old_value} -> new: {value}")
            if old_value == 1 and value == 0:
                return True
            else:
                return False

        def callback_zebra(value, old_value, **kwargs):
            if old_value == 1 and value == 0:
                return True
            return False

        zebra_status = SubscriptionStatus(self.zebra.pc.arm.output, callback_zebra, run=False)

        # motion_status = SubscriptionStatus(self.vector.active, callback_motion, run=False)
        # as an alternative, consider using self.zebra.download_status as the zebra should
        # finish after the vector has finished its movement.
        return zebra_status

    def configure_vector(self, **kwargs):
        logger.debug("configuring vector")
        angle_start = kwargs["angle_start"]
        scan_width = kwargs["scan_width"]
        exposure_ms = kwargs["exposure_period_per_image"] * 1.0e3
        num_images = kwargs["num_images"]
        x_mm = (kwargs["x_start_um"] / 1000, kwargs["x_end_um"] / 1000)
        y_mm = (kwargs["y_start_um"] / 1000, kwargs["y_end_um"] / 1000)
        z_mm = (kwargs["z_start_um"] / 1000, kwargs["z_end_um"] / 1000)
        o = (angle_start, angle_start + scan_width)
        buffer_time_ms = 0
        shutter_lag_time_ms = 2
        shutter_time_ms = 2
        self.vector.prepare_move(
            o,
            x_mm,
            y_mm,
            z_mm,
            exposure_ms,
            num_images,
            buffer_time_ms,
            shutter_lag_time_ms,
            shutter_time_ms,
        )
        logger.debug("configure done")

    def zebra_daq_prep(self):
        self.zebra.reset.put(1)
        ttime.sleep(2.0)  # TODO: very long sleep here
        self.zebra.out1.put(31)
        self.zebra.m1_set_pos.put(1)
        self.zebra.m2_set_pos.put(1)
        self.zebra.m3_set_pos.put(1)
        self.zebra.pc.arm.trig_source.put(0)  # Soft triggering for NYX
