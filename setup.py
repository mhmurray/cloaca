from setuptools import setup
import minify.command

setup(name='cloaca',
        version='0.1.0',
        url='https://github.com/mhmurray/cloaca',
        author='Michael Murray',
        author_email='michaelhamburgmurray@gmail.com',
        license='MIT',
        packages=['cloaca'],
        zip_safe=False,
        include_package_data=True,
        scripts=[
            'cloaca/cloacaapp.py'
            ],
        install_requires=[
            'tornado>=4.3.0',
            'tornadis>=0.7.0',
            'bcrypt>=2.0.0',
            'futures>=3.0.5',
            'minify',
            ],
        cmdclass={
            'minify_js' : minify.command.minify_js,
            'minify_css' : minify.command.minify_css,
            },
        )
