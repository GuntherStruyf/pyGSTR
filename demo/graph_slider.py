'''Methods to easily visualize/plot ImageDump data'''
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, Button, RadioButtons


def generate_sine_data(time, amplitude, frequency):
    '''Self explanatory'''
    signal = amplitude * np.sin(2 * np.pi * frequency * time)
    return signal


def demo():
    '''demo slider'''
    fig, _ = plt.subplots()
    plt.subplots_adjust(left=0.25, bottom=0.25)

    frequency0 = 3.0
    amplitude0 = 5.0
    time = np.arange(0.0, 1.0, 0.001)
    signal = generate_sine_data(time=time,
                                amplitude=amplitude0,
                                frequency=frequency0)
    sine_lines, = plt.plot(time, signal, lw=2, color='red')
    plt.axis([0, 1, -10, 10])

    axcolor = 'lightgoldenrodyellow'
    axfreq = plt.axes([0.25, 0.1, 0.65, 0.03], facecolor=axcolor)
    axamp = plt.axes([0.25, 0.15, 0.65, 0.03], facecolor=axcolor)

    slider_frequency = Slider(axfreq, 'Freq', 0.1, 30.0,
                              valinit=frequency0, valstep=0.1)
    slider_amplitude = Slider(axamp, 'Amp', 0.1, 10.0, valinit=amplitude0)

    def update(val):
        # pylint: disable=unused-argument
        sine_lines.set_ydata(generate_sine_data(time,
                                                slider_frequency.val,
                                                slider_amplitude.val))
        fig.canvas.draw_idle()
    slider_frequency.on_changed(update)
    slider_amplitude.on_changed(update)

    resetax = plt.axes([0.8, 0.025, 0.1, 0.04])
    button = Button(resetax, 'Reset', color=axcolor, hovercolor='0.975')

    def reset(event):
        # pylint: disable=unused-argument
        slider_frequency.reset()
        slider_amplitude.reset()
    button.on_clicked(reset)

    rax = plt.axes([0.025, 0.5, 0.15, 0.15], facecolor=axcolor)
    radio = RadioButtons(rax, ('red', 'blue', 'green'), active=0)

    def colorfunc(label):
        sine_lines.set_color(label)
        fig.canvas.draw_idle()
    radio.on_clicked(colorfunc)

    plt.show()


demo()
