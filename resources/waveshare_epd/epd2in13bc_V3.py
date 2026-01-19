import logging

from . import epdconfig

# Display resolution
EPD_WIDTH = 104
EPD_HEIGHT = 212

logger = logging.getLogger(__name__)


class EPD:
    def __init__(self):
        self.is_initialized = False
        self.reset_pin = epdconfig.RST_PIN
        self.dc_pin = epdconfig.DC_PIN
        self.busy_pin = epdconfig.BUSY_PIN
        self.cs_pin = epdconfig.CS_PIN
        self.width = EPD_WIDTH
        self.height = EPD_HEIGHT

        # Compatibility list for Bjorn
        self.lut_partial_update = []

        self.last_buffer_black = None
        self.last_buffer_colored = None

    def reset(self):
        epdconfig.digital_write(self.reset_pin, 1)
        epdconfig.delay_ms(200)
        epdconfig.digital_write(self.reset_pin, 0)
        epdconfig.delay_ms(2)
        epdconfig.digital_write(self.reset_pin, 1)
        epdconfig.delay_ms(200)

    def send_command(self, command):
        epdconfig.digital_write(self.dc_pin, 0)
        epdconfig.digital_write(self.cs_pin, 0)
        epdconfig.spi_writebyte([command])
        epdconfig.digital_write(self.cs_pin, 1)

    def send_data(self, data):
        epdconfig.digital_write(self.dc_pin, 1)
        epdconfig.digital_write(self.cs_pin, 0)
        epdconfig.spi_writebyte([data])
        epdconfig.digital_write(self.cs_pin, 1)

    def send_data2(self, data):
        epdconfig.digital_write(self.dc_pin, 1)
        epdconfig.digital_write(self.cs_pin, 0)
        epdconfig.spi_writebyte2(data)
        epdconfig.digital_write(self.cs_pin, 1)

    def ReadBusy(self):
        logger.debug("e-Paper busy")
        self.send_command(0x71)
        while epdconfig.digital_read(self.busy_pin) == 0:
            self.send_command(0x71)
            epdconfig.delay_ms(100)
        logger.debug("e-Paper busy release")

    def init(self, update=None):
        # Always perform full init sequences for B/C screens
        if self.is_initialized:
            # Optional: return 0 here if you want to skip re-init,
            # but strictly speaking, re-init is safer after sleep.
            pass

        if epdconfig.module_init() != 0:
            return -1

        self.reset()

        self.send_command(0x04)
        self.ReadBusy()

        self.send_command(0x00)
        self.send_data(0x0F)
        self.send_data(0x89)

        self.send_command(0x61)
        self.send_data(0x68)
        self.send_data(0x00)
        self.send_data(0xD4)

        self.send_command(0x50)
        self.send_data(0x77)

        self.is_initialized = True
        return 0

    def getbuffer(self, image):
        buf = [0xFF] * (int(self.width / 8) * self.height)
        image_monocolor = image.convert("1")
        imwidth, imheight = image_monocolor.size
        pixels = image_monocolor.load()

        if imwidth == self.width and imheight == self.height:
            for y in range(imheight):
                for x in range(imwidth):
                    if pixels[x, y] == 0:
                        buf[int((x + y * self.width) / 8)] &= ~(0x80 >> (x % 8))
        elif imwidth == self.height and imheight == self.width:
            for y in range(imheight):
                for x in range(imwidth):
                    newx = y
                    newy = self.height - x - 1
                    if pixels[x, y] == 0:
                        buf[int((newx + newy * self.width) / 8)] &= ~(0x80 >> (y % 8))
        return buf

    def display(self, imageblack, imagecolored=None):
        if (
            self.last_buffer_black is not None
            and self.last_buffer_colored is not None
            and imageblack == self.last_buffer_black
            and imagecolored == self.last_buffer_colored
        ):
            # Розкоментуйте рядок нижче для налагодження, щоб бачити в консолі, коли оновлення пропускається
            # print("System: Зображення не змінилось. Оновлення пропущено.")
            return

        # Якщо дані нові, зберігаємо їх у пам'ять для наступної перевірки
        # Ми робимо list(), щоб створити копію даних, а не посилання
        self.last_buffer_black = list(imageblack)
        self.last_buffer_colored = list(imagecolored)
        # -----------------------------------

        if not isinstance(imageblack, list):
            imageblack = list(imageblack)

        # Standard Full Refresh
        self.send_command(0x10)
        self.send_data2(imageblack)

        self.send_command(0x13)
        if imagecolored is not None:
            if not isinstance(imagecolored, list):
                imagecolored = list(imagecolored)
            self.send_data2(imagecolored)
        else:
            empty_buf = [0xFF] * (int(self.width * self.height / 8))
            self.send_data2(empty_buf)

        self.send_command(0x12)
        epdconfig.delay_ms(100)
        self.ReadBusy()

    # --- RESTORED WORKING LOGIC ---

    def displayPartial(self, image):
        # REVERT TO VERSION 1: Emulate partial update using full update.
        # This fixes the "strip" issue because we stop using broken 0x90/0x91 commands.
        # self.display(image, None)
        self.display(None, image)

    def Clear(self):
        buf_size = int(self.width * self.height / 8)
        empty_buf = [0xFF] * buf_size

        self.send_command(0x10)
        self.send_data2(empty_buf)
        self.send_command(0x13)
        self.send_data2(empty_buf)
        self.send_command(0x12)
        epdconfig.delay_ms(100)
        self.ReadBusy()

    def sleep(self):
        self.send_command(0x50)
        self.send_data(0xF7)
        self.send_command(0x02)
        self.ReadBusy()
        self.send_command(0x07)
        self.send_data(0xA5)

        epdconfig.delay_ms(2000)
        epdconfig.module_exit()
        self.is_initialized = False

    # Stubs for compatibility
    def TurnOnDisplayPart(self):
        pass

    def displayPartBaseImage(self, image):
        self.display(image, None)

    def SetWindow(self, x_start, y_start, x_end, y_end):
        pass

    def SetCursor(self, x, y):
        pass

    def Lut(self, lut):
        pass

    def SetLut(self, lut):
        pass


### END OF FILE ###
