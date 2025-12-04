import {Spin} from 'antd'

const Loading: React.FC = () => {
    return (
        <Spin fullscreen size='large' tip='Loading...' />
    )
}

export default Loading;